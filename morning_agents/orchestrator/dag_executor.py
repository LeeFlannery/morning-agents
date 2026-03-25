from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp import ClientSession

    from morning_agents.agents.base import BaseAgent
    from morning_agents.contracts.models import AgentResult

logger = logging.getLogger(__name__)


class DAGExecutionError(Exception):
    """Raised when the dependency graph is invalid (cycle or configuration error)."""


@dataclass
class DAGExecutionResult:
    results: dict[str, "AgentResult"]
    tiers: list[list[str]]
    failed: set[str] = field(default_factory=set)


def _make_error_result(agent: "BaseAgent", error_msg: str) -> "AgentResult":
    from morning_agents.contracts.models import AgentResult, AgentStatus, FindingSummary

    now = datetime.now(tz=timezone.utc)
    return AgentResult(
        agent_name=agent.name,
        agent_display_name=agent.display_name,
        status=AgentStatus.error,
        started_at=now,
        completed_at=now,
        duration_ms=0,
        findings=[],
        summary=FindingSummary(total=0, by_severity={}),
        tool_calls=[],
        error=error_msg,
    )


async def execute_dag(
    agents: dict[str, "BaseAgent"],
    sessions: dict[str, "ClientSession"],
    semaphore: asyncio.Semaphore,
) -> DAGExecutionResult:
    """
    Execute agents in topological order based on their depends_on declarations.

    Dependencies are soft: if a declared dependency is not in the agents dict
    (e.g. user ran a subset of agents), it is silently ignored rather than
    raising an error.

    Agents at the same depth tier run concurrently. Each agent receives the
    completed results of its dependencies as `upstream`. If an agent fails,
    its dependents are skipped but the rest of the run continues.
    """
    # Soft deps: only wait for agents that are actually in this run
    graph = {
        name: {dep for dep in agent.depends_on if dep in agents}
        for name, agent in agents.items()
    }

    try:
        sorter = TopologicalSorter(graph)
        sorter.prepare()
    except CycleError as e:
        raise DAGExecutionError(f"Cycle detected in agent dependencies: {e}") from e

    results: dict[str, "AgentResult"] = {}
    failed: set[str] = set()
    tiers: list[list[str]] = []

    while sorter.is_active():
        ready = list(sorter.get_ready())
        if not ready:
            continue

        tiers.append(ready)

        async def run_one(name: str) -> None:
            agent = agents[name]

            # Skip if any active dependency failed
            failed_deps = {dep for dep in agent.depends_on if dep in agents and dep in failed}
            if failed_deps:
                logger.warning("Skipping '%s': dependencies failed: %s", name, failed_deps)
                results[name] = _make_error_result(
                    agent, f"Skipped: dependencies failed: {', '.join(sorted(failed_deps))}"
                )
                failed.add(name)
                sorter.done(name)
                return

            # Check required MCP sessions are available
            missing_sessions = set(agent.mcp_servers) - set(sessions.keys())
            if missing_sessions:
                msg = f"MCP servers unavailable: {', '.join(sorted(missing_sessions))}"
                logger.error("Agent '%s': %s", name, msg)
                results[name] = _make_error_result(agent, msg)
                failed.add(name)
                sorter.done(name)
                return

            # Build upstream dict from completed dependencies
            upstream = None
            if agent.depends_on:
                upstream = {dep: results[dep] for dep in agent.depends_on if dep in results}

            try:
                async with semaphore:
                    result = await agent.run(sessions, upstream)
                result.compute_summary()
                results[name] = result
                logger.info(
                    "Agent '%s' completed: %s (%dms, %d findings)",
                    name,
                    result.status,
                    result.duration_ms,
                    len(result.findings),
                )
            except asyncio.TimeoutError:
                msg = "Agent timed out"
                logger.error("Agent '%s' timed out", name)
                results[name] = _make_error_result(agent, msg)
                failed.add(name)
            except Exception as e:
                msg = f"Unhandled error: {type(e).__name__}: {e}"
                logger.error("Agent '%s' raised: %s", name, e, exc_info=True)
                results[name] = _make_error_result(agent, msg)
                failed.add(name)
            finally:
                sorter.done(name)

        await asyncio.gather(*(run_one(n) for n in ready))

    if failed:
        logger.warning("Agents that failed or were skipped: %s", failed)

    return DAGExecutionResult(results=results, tiers=tiers, failed=failed)
