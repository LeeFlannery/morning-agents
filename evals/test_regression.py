"""Unit tests for regression detection. No API keys needed."""
from datetime import datetime, timezone

import pytest

from evals.regression import RegressionFlag, detect_regressions
from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    BriefingConfig,
    BriefingOutput,
    BriefingSummary,
    ExecutionMeta,
    Finding,
    FindingSummary,
    Severity,
)


def _make_finding(id: str, agent: str, detail: str = "some detail", severity: Severity = Severity.info) -> Finding:
    now = datetime.now(tz=timezone.utc)
    return Finding(
        id=id,
        source_agent=agent,
        category="test",
        severity=severity,
        title=f"Finding {id}",
        detail=detail,
        metadata={"tool_id": "test"},
        timestamp=now,
    )


def _make_result(
    agent_name: str,
    status: AgentStatus = AgentStatus.success,
    findings: list[Finding] | None = None,
    error: str | None = None,
) -> AgentResult:
    now = datetime.now(tz=timezone.utc)
    f = findings or []
    by_sev: dict[str, int] = {}
    for finding in f:
        by_sev[finding.severity.value] = by_sev.get(finding.severity.value, 0) + 1
    return AgentResult(
        agent_name=agent_name,
        agent_display_name=agent_name,
        status=status,
        started_at=now,
        completed_at=now,
        duration_ms=100,
        findings=f,
        summary=FindingSummary(total=len(f), by_severity=by_sev),
        tool_calls=[],
        error=error,
    )


def _make_briefing(results: list[AgentResult], stages: list[list[str]] | None = None) -> BriefingOutput:
    now = datetime.now(tz=timezone.utc)
    stages = stages or [["brewmaster", "devenv"]]
    return BriefingOutput(
        version="0.1.001",
        briefing_id="brief-test",
        generated_at=now,
        duration_ms=1000,
        agent_results=results,
        cross_references=[],
        summary=BriefingSummary(
            agents_run=len(results),
            agents_succeeded=sum(1 for r in results if r.status == AgentStatus.success),
            agents_failed=sum(1 for r in results if r.status == AgentStatus.error),
            total_findings=sum(len(r.findings) for r in results),
            by_severity={},
            mcp_servers_used=2,
        ),
        execution=ExecutionMeta(
            stages=stages,
            dependency_graph={r.agent_name: [] for r in results},
            retries={},
        ),
        config=BriefingConfig(agents_enabled=[r.agent_name for r in results]),
    )


def test_no_regressions():
    findings = [_make_finding("f1", "brewmaster")]
    baseline = _make_briefing([_make_result("brewmaster", findings=findings)])
    current = _make_briefing([_make_result("brewmaster", findings=findings)])
    assert detect_regressions(baseline, current) == []


def test_agent_failure_detected():
    baseline = _make_briefing([_make_result("brewmaster")])
    current = _make_briefing([_make_result("brewmaster", status=AgentStatus.error, error="timeout")])
    flags = detect_regressions(baseline, current)
    assert any(f.flag_type == "agent_failure" and f.severity == "critical" for f in flags)


def test_finding_count_drop_detected():
    b_findings = [_make_finding(f"f{i}", "brewmaster") for i in range(10)]
    c_findings = [_make_finding("f1", "brewmaster")]
    baseline = _make_briefing([_make_result("brewmaster", findings=b_findings)])
    current = _make_briefing([_make_result("brewmaster", findings=c_findings)])
    flags = detect_regressions(baseline, current)
    assert any(f.flag_type == "finding_count_drop" for f in flags)


def test_no_count_drop_when_above_threshold():
    b_findings = [_make_finding(f"f{i}", "brewmaster") for i in range(4)]
    c_findings = [_make_finding(f"f{i}", "brewmaster") for i in range(3)]
    baseline = _make_briefing([_make_result("brewmaster", findings=b_findings)])
    current = _make_briefing([_make_result("brewmaster", findings=c_findings)])
    flags = detect_regressions(baseline, current)
    assert not any(f.flag_type == "finding_count_drop" for f in flags)


def test_detail_quality_drop_detected():
    b_findings = [_make_finding("f1", "brewmaster", detail="x" * 200)]
    c_findings = [_make_finding("f1", "brewmaster", detail="x" * 10)]
    baseline = _make_briefing([_make_result("brewmaster", findings=b_findings)])
    current = _make_briefing([_make_result("brewmaster", findings=c_findings)])
    flags = detect_regressions(baseline, current)
    assert any(f.flag_type == "detail_quality_drop" for f in flags)


def test_dag_stage_change_detected():
    results = [_make_result("brewmaster")]
    baseline = _make_briefing(results, stages=[["brewmaster"]])
    current = _make_briefing(results, stages=[["brewmaster"], ["devenv"]])
    flags = detect_regressions(baseline, current)
    assert any(f.flag_type == "dag_stage_change" for f in flags)


def test_missing_agent_in_current_skipped():
    baseline = _make_briefing([_make_result("brewmaster"), _make_result("devenv")])
    current = _make_briefing([_make_result("brewmaster")])
    flags = detect_regressions(baseline, current)
    assert not any(f.agent_name == "devenv" for f in flags)
