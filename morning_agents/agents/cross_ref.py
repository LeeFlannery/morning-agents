from __future__ import annotations

from datetime import datetime, timezone

from mcp import ClientSession

from morning_agents.agents.base import BaseAgent
from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    Finding,
    FindingSummary,
    Severity,
)
from morning_agents.skills.cross_reference import find_cross_references
from morning_agents.skills.timing import elapsed_ms


class CrossRefAgent(BaseAgent):
    name = "cross_ref"
    display_name = "🔗 Cross-Reference"
    mcp_servers = []
    depends_on = ["brewmaster", "devenv", "pr_queue"]

    def get_system_prompt(self) -> str:
        return ""  # No Claude call; pure correlation logic

    async def run(
        self,
        sessions: dict[str, ClientSession],
        upstream: dict[str, AgentResult] | None = None,
    ) -> AgentResult:
        started_at = datetime.now(tz=timezone.utc)

        if not upstream:
            completed_at = datetime.now(tz=timezone.utc)
            return AgentResult(
                agent_name=self.name,
                agent_display_name=self.display_name,
                status=AgentStatus.success,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=elapsed_ms(started_at, completed_at),
                findings=[],
                summary=FindingSummary(total=0, by_severity={}),
                tool_calls=[],
            )

        cross_refs = find_cross_references(list(upstream.values()))

        findings: list[Finding] = []
        now = datetime.now(tz=timezone.utc)

        for xref in cross_refs:
            findings.append(Finding(
                id=xref.id,
                source_agent=self.name,
                category="cross_reference",
                severity=xref.severity,
                title=xref.title,
                detail=xref.detail,
                metadata={
                    "source_findings": xref.source_findings,
                    "source_agents": xref.source_agents,
                },
                timestamp=now,
            ))

        completed_at = datetime.now(tz=timezone.utc)
        return AgentResult(
            agent_name=self.name,
            agent_display_name=self.display_name,
            status=AgentStatus.success,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=elapsed_ms(started_at, completed_at),
            findings=findings,
            summary=FindingSummary(total=len(findings), by_severity={
                Severity.warning.value: sum(1 for f in findings if f.severity == Severity.warning),
                Severity.action_needed.value: sum(1 for f in findings if f.severity == Severity.action_needed),
            } if findings else {},),
            tool_calls=[],
        )
