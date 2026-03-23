from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from morning_agents.contracts.models import AgentResult, CrossReference, Finding, Severity


class CorrelationRule(ABC):
    """Abstract base class for cross-reference correlation rules."""

    @abstractmethod
    def apply(self, results: list[AgentResult]) -> list[CrossReference]:
        """Apply the rule to agent results and return any cross-references found."""
        ...


class NodeUpgradeVsPRRule(CorrelationRule):
    """
    Finds node upgrade findings (tool_id == 'node', severity warning/action_needed)
    and PRs with node keywords in title, then correlates them.
    """

    _NODE_KEYWORDS = {"node", "nodejs", "node.js", "npm", "nvm"}

    def apply(self, results: list[AgentResult]) -> list[CrossReference]:
        node_findings: list[Finding] = []
        pr_findings: list[Finding] = []

        for result in results:
            for finding in result.findings:
                tool_id = finding.metadata.get("tool_id", "")
                if (
                    tool_id == "node"
                    and finding.severity in (Severity.warning, Severity.action_needed)
                ):
                    node_findings.append(finding)
                elif tool_id == "github_pr":
                    title_lower = finding.title.lower()
                    if any(kw in title_lower for kw in self._NODE_KEYWORDS):
                        pr_findings.append(finding)

        if not node_findings or not pr_findings:
            return []

        source_finding_ids = [f.id for f in node_findings + pr_findings]
        source_agents = list({f.source_agent for f in node_findings + pr_findings})

        node_titles = ", ".join(f.title for f in node_findings)
        pr_titles = ", ".join(f.title for f in pr_findings)

        return [
            CrossReference(
                id=f"xref-node-pr-{uuid.uuid4().hex[:8]}",
                severity=Severity.warning,
                title="Node.js upgrade may affect open PRs",
                detail=(
                    f"Node upgrade detected ({node_titles}) and "
                    f"Node-related PRs are open ({pr_titles}). "
                    "Consider coordinating the upgrade with PR merges."
                ),
                source_findings=source_finding_ids,
                source_agents=source_agents,
                timestamp=datetime.now(tz=timezone.utc),
            )
        ]


CORRELATION_RULES: list[CorrelationRule] = [
    NodeUpgradeVsPRRule(),
]


def find_cross_references(results: list[AgentResult]) -> list[CrossReference]:
    """Apply all correlation rules and return the combined list of cross-references."""
    cross_refs: list[CrossReference] = []
    for rule in CORRELATION_RULES:
        cross_refs.extend(rule.apply(results))
    return cross_refs
