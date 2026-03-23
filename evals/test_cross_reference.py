"""
Unit tests for morning_agents.skills.cross_reference.
No API calls — uses mock AgentResult and Finding objects.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    Finding,
    FindingSummary,
    Severity,
)
from morning_agents.skills.cross_reference import (
    NodeUpgradeVsPRRule,
    find_cross_references,
)


def _now():
    return datetime.now(tz=timezone.utc)


def _make_result(agent_name: str, findings: list[Finding]) -> AgentResult:
    now = _now()
    r = AgentResult(
        agent_name=agent_name,
        agent_display_name=agent_name,
        status=AgentStatus.success,
        started_at=now,
        completed_at=now,
        duration_ms=100,
        findings=findings,
    )
    r.compute_summary()
    return r


def _make_finding(
    fid: str,
    source_agent: str,
    title: str,
    severity: Severity = Severity.info,
    metadata: dict | None = None,
) -> Finding:
    return Finding(
        id=fid,
        source_agent=source_agent,
        category="test",
        severity=severity,
        title=title,
        detail="test detail",
        metadata=metadata or {},
        timestamp=_now(),
    )


def test_no_results_returns_empty():
    """find_cross_references with empty results returns empty list."""
    result = find_cross_references([])
    assert result == []


def test_node_upgrade_no_prs():
    """Node upgrade finding but no node-related PRs → no cross-references."""
    node_finding = _make_finding(
        "devenv-001",
        "devenv",
        "Node: 18.0.0 → 20.0.0 (major)",
        severity=Severity.warning,
        metadata={"tool_id": "node"},
    )
    result = _make_result("devenv", [node_finding])
    refs = find_cross_references([result])
    assert refs == []


def test_node_upgrade_with_matching_pr():
    """Node upgrade finding + node PR → one cross-reference produced."""
    node_finding = _make_finding(
        "devenv-001",
        "devenv",
        "Node: 18.0.0 → 20.0.0 (major)",
        severity=Severity.warning,
        metadata={"tool_id": "node"},
    )
    pr_finding = _make_finding(
        "pr-001",
        "pr_queue",
        "myorg/myrepo#42: Upgrade node.js to v20",
        severity=Severity.action_needed,
        metadata={"tool_id": "github_pr"},
    )
    devenv_result = _make_result("devenv", [node_finding])
    pr_result = _make_result("pr_queue", [pr_finding])

    refs = find_cross_references([devenv_result, pr_result])
    assert len(refs) == 1
    xref = refs[0]
    assert xref.severity == Severity.warning
    assert "node" in xref.title.lower() or "Node" in xref.title
    assert "devenv-001" in xref.source_findings
    assert "pr-001" in xref.source_findings
    assert "devenv" in xref.source_agents
    assert "pr_queue" in xref.source_agents


def test_node_upgrade_unrelated_pr():
    """Node upgrade finding + unrelated PR → no cross-reference."""
    node_finding = _make_finding(
        "devenv-001",
        "devenv",
        "Node: 18.0.0 → 20.0.0 (major)",
        severity=Severity.warning,
        metadata={"tool_id": "node"},
    )
    pr_finding = _make_finding(
        "pr-001",
        "pr_queue",
        "myorg/myrepo#5: Fix typo in README",
        severity=Severity.info,
        metadata={"tool_id": "github_pr"},
    )
    devenv_result = _make_result("devenv", [node_finding])
    pr_result = _make_result("pr_queue", [pr_finding])

    refs = find_cross_references([devenv_result, pr_result])
    assert refs == []


def test_multiple_rules_compose():
    """find_cross_references collects results from all rules."""
    # Test that with matching data, at least one rule fires
    node_finding = _make_finding(
        "devenv-001",
        "devenv",
        "Node: 18.0.0 → 20.0.0 (major)",
        severity=Severity.action_needed,
        metadata={"tool_id": "node"},
    )
    pr_finding = _make_finding(
        "pr-002",
        "pr_queue",
        "myorg/repo#10: Update npm dependencies",
        severity=Severity.warning,
        metadata={"tool_id": "github_pr"},
    )
    devenv_result = _make_result("devenv", [node_finding])
    pr_result = _make_result("pr_queue", [pr_finding])

    refs = find_cross_references([devenv_result, pr_result])
    # At minimum, NodeUpgradeVsPRRule should fire since "npm" is in the PR title
    assert len(refs) >= 1
    # All cross-references have required fields
    for ref in refs:
        assert ref.id
        assert ref.title
        assert ref.severity in list(Severity)
        assert ref.timestamp is not None
