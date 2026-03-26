"""Golden test for PRQueueAgent. Requires ANTHROPIC_API_KEY."""
import asyncio
import json
from pathlib import Path

import pytest
import yaml

from evals.judge import judge_agent_output
from evals.mocks import MockMCPSession

GOLDEN_DIR = Path("evals/golden/pr_queue")


@pytest.fixture(scope="module")
def frozen_data() -> dict:
    data = json.loads((GOLDEN_DIR / "search_results.json").read_text())
    return {"search_pull_requests": data["output"]}


@pytest.fixture(scope="module")
def criteria() -> dict:
    return yaml.safe_load((GOLDEN_DIR / "criteria.yaml").read_text())


@pytest.fixture(scope="module")
async def agent_output(frozen_data):
    from morning_agents.agents.pr_queue import PRQueueAgent
    from morning_agents.orchestrator.resources import ResourceContext

    ctx = ResourceContext(
        semaphore=asyncio.Semaphore(4),
        workspace_root=Path("/tmp/morning-agents-eval"),
        briefing_id="eval",
    )
    agent = PRQueueAgent(resources=ctx)
    mock_session = MockMCPSession(frozen_data)
    result = await agent.run(
        sessions={"github-mcp": mock_session},
        upstream=None,
    )
    result.compute_summary()
    return result


async def test_golden_pr_queue(agent_output, criteria, frozen_data):
    verdict = await judge_agent_output(
        agent_name="pr_queue",
        findings=[f.model_dump() for f in agent_output.findings],
        criteria=criteria,
        frozen_input=frozen_data,
    )
    for r in verdict.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.check_id}: {r.reasoning[:120]}")
    print(f"\n  Score: {verdict.score:.0%} ({verdict.passed}/{verdict.total_checks})")
    assert verdict.score >= 0.8, f"PR Queue quality below threshold: {verdict.score:.0%}"
