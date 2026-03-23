"""
Integration test for the PR Queue agent.
Starts github-mcp, runs PRQueueAgent once, validates AgentResult contract.
Requires ANTHROPIC_API_KEY and GITHUB_TOKEN in environment (use: op run --env-file=op.env -- uv run pytest)
"""
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from morning_agents.agents.pr_queue import PRQueueAgent
from morning_agents.config import GITHUB_MCP
from morning_agents.contracts.models import AgentResult, AgentStatus, Severity


@pytest.fixture(scope="module")
def agent():
    return PRQueueAgent()


@pytest.fixture(scope="module")
async def result(agent) -> AgentResult:
    async with stdio_client(GITHUB_MCP) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            r = await agent.run({"github-mcp": session})
            r.compute_summary()
            return r


async def test_pr_queue_returns_agent_result(result):
    assert result.agent_name == "pr_queue"
    assert result.agent_display_name == "🔀 PR Queue"
    assert result.status == AgentStatus.success
    assert result.started_at is not None
    assert result.completed_at >= result.started_at
    assert result.duration_ms > 0


async def test_pr_queue_has_findings(result):
    assert len(result.findings) > 0
    for f in result.findings:
        assert f.id.startswith("pr-")
        assert f.source_agent == "pr_queue"
        assert f.severity in list(Severity)
        assert f.title
        assert f.timestamp is not None
        assert f.timestamp.tzinfo is not None


async def test_pr_queue_has_summary(result):
    assert result.summary is not None
    assert result.summary.total == len(result.findings)
    assert sum(result.summary.by_severity.values()) == result.summary.total


async def test_pr_queue_tool_calls_logged(result):
    tool_names = {tc.tool for tc in result.tool_calls}
    # At minimum we expect the Claude call
    assert "messages.create" in tool_names
    for tc in result.tool_calls:
        assert tc.success
        assert tc.duration_ms > 0
