from __future__ import annotations

from dataclasses import dataclass

from morning_agents.contracts.models import AgentStatus, BriefingOutput


@dataclass
class RegressionFlag:
    agent_name: str
    flag_type: str
    severity: str
    description: str
    baseline_value: str
    current_value: str


def detect_regressions(
    baseline: BriefingOutput,
    current: BriefingOutput,
    finding_count_threshold: float = 0.5,
    detail_length_threshold: float = 0.4,
) -> list[RegressionFlag]:
    flags: list[RegressionFlag] = []

    baseline_agents = {r.agent_name: r for r in baseline.agent_results}
    current_agents = {r.agent_name: r for r in current.agent_results}

    for agent_name, baseline_result in baseline_agents.items():
        current_result = current_agents.get(agent_name)
        if current_result is None:
            continue

        if baseline_result.status == AgentStatus.success and current_result.status == AgentStatus.error:
            flags.append(RegressionFlag(
                agent_name=agent_name,
                flag_type="agent_failure",
                severity="critical",
                description=f"{agent_name} succeeded in baseline but failed in current run",
                baseline_value="success",
                current_value=f"error: {current_result.error or 'unknown'}",
            ))
            continue

        b_count = len(baseline_result.findings)
        c_count = len(current_result.findings)
        if b_count > 0 and c_count < b_count * (1 - finding_count_threshold):
            flags.append(RegressionFlag(
                agent_name=agent_name,
                flag_type="finding_count_drop",
                severity="warning",
                description=f"{agent_name} findings: {b_count} → {c_count}",
                baseline_value=str(b_count),
                current_value=str(c_count),
            ))

        b_sev = baseline_result.summary.by_severity if baseline_result.summary else {}
        c_sev = current_result.summary.by_severity if current_result.summary else {}
        b_action = b_sev.get("action_needed", 0)
        c_action = c_sev.get("action_needed", 0)
        if b_action > 0 and c_action >= b_action * 3:
            flags.append(RegressionFlag(
                agent_name=agent_name,
                flag_type="severity_shift",
                severity="warning",
                description=f"{agent_name} action_needed: {b_action} → {c_action}",
                baseline_value=str(b_action),
                current_value=str(c_action),
            ))

        if baseline_result.findings and current_result.findings:
            b_avg = sum(len(f.detail) for f in baseline_result.findings) / len(baseline_result.findings)
            c_avg = sum(len(f.detail) for f in current_result.findings) / len(current_result.findings)
            if b_avg > 0 and c_avg < b_avg * (1 - detail_length_threshold):
                flags.append(RegressionFlag(
                    agent_name=agent_name,
                    flag_type="detail_quality_drop",
                    severity="warning",
                    description=f"{agent_name} avg detail: {b_avg:.0f} → {c_avg:.0f} chars",
                    baseline_value=f"{b_avg:.0f}",
                    current_value=f"{c_avg:.0f}",
                ))

    if baseline.execution and current.execution:
        if baseline.execution.stages != current.execution.stages:
            flags.append(RegressionFlag(
                agent_name="_orchestrator",
                flag_type="dag_stage_change",
                severity="warning",
                description="DAG execution stages changed between runs",
                baseline_value=str(baseline.execution.stages),
                current_value=str(current.execution.stages),
            ))

    return flags
