"""Golden test for BrewmasterAgent. Requires ANTHROPIC_API_KEY."""
import asyncio
import json
from pathlib import Path

import pytest
import yaml

from evals.judge import judge_agent_output
from evals.mocks import MockMCPSession

GOLDEN_DIR = Path("evals/golden/brewmaster")


@pytest.fixture(scope="module")
def frozen_data() -> dict:
    outdated = json.loads((GOLDEN_DIR / "outdated_packages.json").read_text())
    doctor = json.loads((GOLDEN_DIR / "doctor_warnings.json").read_text())
    return {
        "list_outdated": outdated["output"],
        "get_doctor_status": doctor["output"],
    }


@pytest.fixture(scope="module")
def criteria() -> dict:
    return yaml.safe_load((GOLDEN_DIR / "criteria.yaml").read_text())


@pytest.fixture(scope="module")
async def agent_output(frozen_data):
    from morning_agents.agents.brewmaster import BrewmasterAgent
    from morning_agents.orchestrator.resources import ResourceContext

    ctx = ResourceContext(
        semaphore=asyncio.Semaphore(4),
        workspace_root=Path("/tmp/morning-agents-eval"),
        briefing_id="eval",
    )
    agent = BrewmasterAgent(resources=ctx)
    mock_session = MockMCPSession(frozen_data)
    result = await agent.run(
        sessions={"homebrew-mcp": mock_session},
        upstream=None,
    )
    result.compute_summary()
    return result


async def test_golden_brewmaster(agent_output, criteria, frozen_data):
    verdict = await judge_agent_output(
        agent_name="brewmaster",
        findings=[f.model_dump() for f in agent_output.findings],
        criteria=criteria,
        frozen_input=frozen_data,
    )
    for r in verdict.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.check_id}: {r.reasoning[:120]}")
    print(f"\n  Score: {verdict.score:.0%} ({verdict.passed}/{verdict.total_checks})")
    assert verdict.score >= 0.8, f"Brewmaster quality below threshold: {verdict.score:.0%}"
