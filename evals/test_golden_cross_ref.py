"""Golden test for CrossRefAgent (depth-1). Requires ANTHROPIC_API_KEY."""
import asyncio
from pathlib import Path

import pytest
import yaml

from evals.judge import judge_agent_output
from evals.mocks import load_upstream_fixture

GOLDEN_DIR = Path("evals/golden/cross_ref")


@pytest.fixture(scope="module")
def upstream():
    return load_upstream_fixture(str(GOLDEN_DIR / "upstream_results.json"))


@pytest.fixture(scope="module")
def criteria() -> dict:
    return yaml.safe_load((GOLDEN_DIR / "criteria.yaml").read_text())


@pytest.fixture(scope="module")
async def agent_output(upstream):
    from morning_agents.agents.cross_ref import CrossRefAgent
    from morning_agents.orchestrator.resources import ResourceContext

    ctx = ResourceContext(
        semaphore=asyncio.Semaphore(4),
        workspace_root=Path("/tmp/morning-agents-eval"),
        briefing_id="eval",
    )
    agent = CrossRefAgent(resources=ctx)
    result = await agent.run(
        sessions={},
        upstream=upstream,
    )
    result.compute_summary()
    return result


async def test_golden_cross_ref(agent_output, criteria, upstream):
    frozen_input = {name: r.model_dump() for name, r in upstream.items()}
    verdict = await judge_agent_output(
        agent_name="cross_ref",
        findings=[f.model_dump() for f in agent_output.findings],
        criteria=criteria,
        frozen_input=frozen_input,
    )
    for r in verdict.results:
        status = "PASS" if r.passed else "FAIL"
        print(f"  [{status}] {r.check_id}: {r.reasoning[:120]}")
    print(f"\n  Score: {verdict.score:.0%} ({verdict.passed}/{verdict.total_checks})")
    assert verdict.score >= 0.8, f"CrossRef quality below threshold: {verdict.score:.0%}"
