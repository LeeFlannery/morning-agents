"""
Integration test for Orchestrator with BrewmasterAgent.
Starts homebrew-mcp via Orchestrator, runs once, validates BriefingOutput contract.
Requires ANTHROPIC_API_KEY in environment (use: op run --env-file=op.env -- uv run pytest)
"""
import pytest

from morning_agents.agents.brewmaster import BrewmasterAgent
from morning_agents.contracts.models import AgentStatus, BriefingOutput, Severity
from morning_agents.orchestrator import Orchestrator


@pytest.fixture(scope="module")
async def briefing() -> BriefingOutput:
    orchestrator = Orchestrator(agent_classes=[BrewmasterAgent])
    return await orchestrator.run()


async def test_briefing_shape(briefing: BriefingOutput) -> None:
    assert briefing.version == "0.1.002"
    assert briefing.briefing_id.startswith("brief-")
    assert briefing.generated_at is not None
    assert briefing.duration_ms > 0


async def test_briefing_summary(briefing: BriefingOutput) -> None:
    s = briefing.summary
    assert s.agents_run == 1
    assert s.agents_succeeded == 1
    assert s.agents_failed == 0
    assert s.mcp_servers_used == 1
    assert s.total_findings == sum(s.by_severity.values())


async def test_briefing_agent_result(briefing: BriefingOutput) -> None:
    assert len(briefing.agent_results) == 1
    result = briefing.agent_results[0]
    assert result.agent_name == "brewmaster"
    assert result.status == AgentStatus.success
    assert len(result.findings) > 0
    assert result.summary is not None
    assert result.summary.total == len(result.findings)


async def test_briefing_config(briefing: BriefingOutput) -> None:
    assert briefing.config.agents_enabled == ["brewmaster"]
    assert briefing.config.quiet_mode is False


async def test_briefing_severity_values(briefing: BriefingOutput) -> None:
    valid = {s.value for s in Severity}
    for result in briefing.agent_results:
        for finding in result.findings:
            assert finding.severity.value in valid
