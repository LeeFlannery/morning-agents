"""
Integration test for the DevEnv agent.
Starts devenv-mcp, runs DevEnvAgent once, validates AgentResult contract.
Requires ANTHROPIC_API_KEY in environment (use: op run --env-file=op.env -- uv run pytest)
"""
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from morning_agents.agents.devenv import DevEnvAgent
from morning_agents.config import DEVENV_MCP
from morning_agents.contracts.models import AgentResult, AgentStatus, Severity


@pytest.fixture(scope="module")
def agent():
    return DevEnvAgent()


@pytest.fixture(scope="module")
async def result(agent) -> AgentResult:
    async with stdio_client(DEVENV_MCP) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await agent.run({"devenv-mcp": session})


async def test_devenv_returns_agent_result(result):
    assert result.agent_name == "devenv"
    assert result.agent_display_name == "🛠️  DevEnv"
    assert result.status == AgentStatus.success
    assert result.started_at is not None
    assert result.completed_at >= result.started_at
    assert result.duration_ms > 0


async def test_devenv_has_findings(result):
    assert len(result.findings) > 0
    for f in result.findings:
        assert f.id.startswith("devenv-")
        assert f.source_agent == "devenv"
        assert f.severity in list(Severity)
        assert f.title
        assert f.timestamp is not None
        assert f.timestamp.tzinfo is not None


async def test_devenv_has_summary(result):
    assert result.summary is not None
    assert result.summary.total == len(result.findings)
    assert sum(result.summary.by_severity.values()) == result.summary.total


async def test_devenv_tool_calls_logged(result):
    tool_names = {tc.tool for tc in result.tool_calls}
    assert "check_xcode_version" in tool_names
    assert "check_vscode_version" in tool_names
    assert "check_node_version" in tool_names
    assert "check_python_version" in tool_names
    for tc in result.tool_calls:
        assert tc.success
        assert tc.duration_ms > 0


async def test_devenv_covers_expected_tools(result):
    # Claude returns display names (e.g. "Node.js", "Python") not normalized keys.
    # Check case-insensitively that at least node or python are represented.
    tool_names_lower = {
        (f.metadata.get("tool") or "").lower()
        for f in result.findings
        if "tool" in f.metadata
    }
    assert any("node" in t or "python" in t for t in tool_names_lower)
