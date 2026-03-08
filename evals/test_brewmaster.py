"""
Integration test for the Brewmaster agent.
Starts homebrew-mcp, runs BrewmasterAgent once, validates AgentResult contract.
Requires ANTHROPIC_API_KEY in environment (use: op run --env-file=op.env -- uv run pytest)
"""
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from morning_agents.agents.brewmaster import BrewmasterAgent
from morning_agents.contracts.models import AgentResult, AgentStatus, Severity

SERVER_PARAMS = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/homebrew-mcp/index.ts"],
)


@pytest.fixture(scope="module")
def agent():
    return BrewmasterAgent()


@pytest.fixture(scope="module")
async def result(agent) -> AgentResult:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await agent.run({"homebrew-mcp": session})


async def test_brewmaster_returns_agent_result(result):
    assert result.agent_name == "brewmaster"
    assert result.agent_display_name == "🍺 Brewmaster"
    assert result.status == AgentStatus.success
    assert result.started_at is not None
    assert result.completed_at >= result.started_at
    assert result.duration_ms > 0


async def test_brewmaster_has_findings(result):
    assert len(result.findings) > 0
    for f in result.findings:
        assert f.id.startswith("brew-")
        assert f.source_agent == "brewmaster"
        assert f.severity in list(Severity)
        assert f.title
        assert f.detail
        assert f.timestamp is not None
        assert f.timestamp.tzinfo is not None


async def test_brewmaster_has_summary(result):
    assert result.summary is not None
    assert result.summary.total == len(result.findings)
    assert sum(result.summary.by_severity.values()) == result.summary.total


async def test_brewmaster_tool_calls_logged(result):
    tool_names = {tc.tool for tc in result.tool_calls}
    assert "list_outdated" in tool_names
    assert "get_doctor_status" in tool_names
    for tc in result.tool_calls:
        assert tc.success
        assert tc.duration_ms > 0


async def test_brewmaster_severity_mapping(result):
    valid_severities = {s.value for s in Severity}
    for f in result.findings:
        assert f.severity.value in valid_severities
        if f.metadata.get("version_jump") == "major":
            assert f.severity == Severity.action_needed
        if f.metadata.get("version_jump") == "patch":
            assert f.severity == Severity.info
