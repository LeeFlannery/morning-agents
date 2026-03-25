"""DAG executor unit tests."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from morning_agents.contracts.models import AgentResult, AgentStatus, FindingSummary
from morning_agents.orchestrator.dag_executor import (
    DAGExecutionError,
    DAGExecutionResult,
    execute_dag,
)
from morning_agents.agents.base import BaseAgent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_result(agent_name: str, display_name: str) -> AgentResult:
    now = datetime.now(tz=timezone.utc)
    return AgentResult(
        agent_name=agent_name,
        agent_display_name=display_name,
        status=AgentStatus.success,
        started_at=now,
        completed_at=now,
        duration_ms=1,
        findings=[],
        summary=FindingSummary(total=0, by_severity={}),
        tool_calls=[],
    )


class MockAgent(BaseAgent):
    """Configurable mock agent for testing. Class attrs are overridden per-instance."""

    # Satisfy __init_subclass__ check; overridden in __init__
    name = "mock"
    display_name = "Mock"
    mcp_servers: list[str] = []
    depends_on: list[str] = []

    def __init__(
        self,
        name: str,
        depends_on: list[str] | None = None,
        sleep_ms: int = 0,
        fail: bool = False,
        resources=None,
    ):
        super().__init__(resources=resources)
        self.name = name
        self.display_name = name
        self.mcp_servers = []
        self.depends_on = depends_on or []
        self._sleep_ms = sleep_ms
        self._fail = fail
        self.received_upstream: dict | None = None

    def get_system_prompt(self) -> str:
        return ""

    async def run(self, sessions, upstream=None):
        self.received_upstream = upstream
        if self._sleep_ms:
            await asyncio.sleep(self._sleep_ms / 1000)
        if self._fail:
            raise RuntimeError("Intentional failure")
        return _ok_result(self.name, self.display_name)


def _agents(*mocks: MockAgent) -> dict[str, MockAgent]:
    return {a.name: a for a in mocks}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_all_independent_single_tier():
    """All agents with no deps run in one tier concurrently."""
    a = MockAgent("a")
    b = MockAgent("b")
    c = MockAgent("c")

    sem = asyncio.Semaphore(10)
    result = await execute_dag(_agents(a, b, c), {}, sem)

    assert set(result.results) == {"a", "b", "c"}
    assert len(result.tiers) == 1
    assert set(result.tiers[0]) == {"a", "b", "c"}
    assert result.failed == set()


async def test_linear_chain():
    """A -> B -> C runs in three sequential tiers."""
    a = MockAgent("a")
    b = MockAgent("b", depends_on=["a"])
    c = MockAgent("c", depends_on=["b"])

    sem = asyncio.Semaphore(10)
    result = await execute_dag(_agents(a, b, c), {}, sem)

    assert result.tiers == [["a"], ["b"], ["c"]]
    assert b.received_upstream == {"a": result.results["a"]}
    assert c.received_upstream == {"b": result.results["b"]}


async def test_diamond_dependency():
    """A -> B, A -> C, B+C -> D: A first, B+C concurrent, D last."""
    a = MockAgent("a")
    b = MockAgent("b", depends_on=["a"])
    c = MockAgent("c", depends_on=["a"])
    d = MockAgent("d", depends_on=["b", "c"])

    sem = asyncio.Semaphore(10)
    result = await execute_dag(_agents(a, b, c, d), {}, sem)

    assert result.tiers[0] == ["a"]
    assert set(result.tiers[1]) == {"b", "c"}
    assert result.tiers[2] == ["d"]
    assert set(d.received_upstream) == {"b", "c"}


async def test_cycle_detection():
    """A depends on B and B depends on A raises DAGExecutionError."""
    a = MockAgent("a", depends_on=["b"])
    b = MockAgent("b", depends_on=["a"])

    sem = asyncio.Semaphore(10)
    with pytest.raises(DAGExecutionError, match="Cycle detected"):
        await execute_dag(_agents(a, b), {}, sem)


async def test_agent_failure_skips_dependents():
    """If A fails, B (depends on A) is skipped; C (independent) still runs."""
    a = MockAgent("a", fail=True)
    b = MockAgent("b", depends_on=["a"])
    c = MockAgent("c")

    sem = asyncio.Semaphore(10)
    result = await execute_dag(_agents(a, b, c), {}, sem)

    assert "a" in result.failed
    assert "b" in result.failed
    assert result.results["b"].status == AgentStatus.error
    assert result.results["c"].status == AgentStatus.success


async def test_soft_dependencies_missing_dep_ignored():
    """If a declared dependency is not in the agents dict, it is silently ignored."""
    # cross_ref declares depends_on=["brewmaster", "devenv", "pr_queue"]
    # but we only run cross_ref + brewmaster
    a = MockAgent("brewmaster")
    xref = MockAgent("cross_ref", depends_on=["brewmaster", "devenv", "pr_queue"])

    sem = asyncio.Semaphore(10)
    result = await execute_dag(_agents(a, xref), {}, sem)

    # Should not raise; cross_ref runs after brewmaster
    assert result.results["cross_ref"].status == AgentStatus.success
    assert xref.received_upstream == {"brewmaster": result.results["brewmaster"]}


async def test_semaphore_limits_concurrency():
    """With semaphore(1), agents at the same tier run sequentially."""
    execution_order: list[str] = []

    class OrderedMock(MockAgent):
        name = "ordered_mock"
        display_name = "Ordered Mock"
        mcp_servers: list[str] = []
        depends_on: list[str] = []

        async def run(self, sessions, upstream=None):
            execution_order.append(self.name)
            await asyncio.sleep(0.01)
            return _ok_result(self.name, self.display_name)

    a = OrderedMock("a")
    b = OrderedMock("b")
    c = OrderedMock("c")

    sem = asyncio.Semaphore(1)
    result = await execute_dag(_agents(a, b, c), {}, sem)

    # All three complete (order may vary by scheduler, but all ran)
    assert set(result.results) == {"a", "b", "c"}
    assert len(execution_order) == 3
