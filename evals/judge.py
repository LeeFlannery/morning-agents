from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field

import anthropic

from morning_agents.skills.mcp_utils import strip_fences

JUDGE_MODEL = "claude-haiku-4-5-20251001"

_client = anthropic.AsyncAnthropic()


@dataclass
class CheckResult:
    check_id: str
    passed: bool
    reasoning: str


@dataclass
class JudgeVerdict:
    agent_name: str
    total_checks: int
    passed: int
    failed: int
    score: float
    results: list[CheckResult] = field(default_factory=list)


async def judge_agent_output(
    agent_name: str,
    findings: list[dict],
    criteria: dict,
    frozen_input: dict,
) -> JudgeVerdict:
    """Grade an agent's findings against expected criteria using Haiku."""
    async def _judge_one(check: dict) -> CheckResult:
        prompt = _build_judge_prompt(agent_name, findings, check, frozen_input)
        response = await _client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_judge_response(check["id"], response)

    results = await asyncio.gather(*(_judge_one(c) for c in criteria["checks"]))
    passed = sum(1 for r in results if r.passed)
    return JudgeVerdict(
        agent_name=agent_name,
        total_checks=len(results),
        passed=passed,
        failed=len(results) - passed,
        score=passed / len(results) if results else 0.0,
        results=list(results),
    )


def _build_judge_prompt(
    agent_name: str,
    findings: list[dict],
    check: dict,
    frozen_input: dict,
) -> str:
    return f"""You are an evaluation judge for an AI agent called "{agent_name}".

The agent received this input data:
<input>
{json.dumps(frozen_input, indent=2, default=str)[:3000]}
</input>

The agent produced these findings:
<findings>
{json.dumps(findings, indent=2, default=str)[:3000]}
</findings>

Evaluate this specific criterion:
<criterion>
ID: {check["id"]}
Description: {check["description"]}
Expected: {json.dumps(check.get("expected", {}))}
Finding match filter: {json.dumps(check.get("finding_match", {}))}
</criterion>

Think step by step:
1. Find the relevant finding(s) that match the filter (if any)
2. Check whether the finding(s) meet the expected criteria
3. State your conclusion

Respond with ONLY this JSON (no markdown fences, no text outside):
{{"passed": true_or_false, "reasoning": "your step-by-step explanation"}}"""


def _parse_judge_response(check_id: str, response: anthropic.types.Message) -> CheckResult:
    text = strip_fences(response.content[0].text)
    try:
        data = json.loads(text)
        return CheckResult(
            check_id=check_id,
            passed=bool(data.get("passed", False)),
            reasoning=data.get("reasoning", "No reasoning provided"),
        )
    except json.JSONDecodeError:
        return CheckResult(
            check_id=check_id,
            passed=False,
            reasoning=f"Judge returned unparseable response: {text[:200]}",
        )
