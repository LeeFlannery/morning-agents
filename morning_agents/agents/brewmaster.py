from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic
from mcp import ClientSession

from morning_agents.agents.base import BaseAgent
from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    Finding,
    Severity,
    ToolCall,
)
from morning_agents.skills.mcp_utils import parse_tool_result, strip_fences
from morning_agents.skills.semver import classify
from morning_agents.skills.severity import from_version_jump
from morning_agents.skills.timing import ms_timer

_client = anthropic.AsyncAnthropic()


class BrewmasterAgent(BaseAgent):
    name = "brewmaster"
    display_name = "🍺 Brewmaster"
    mcp_servers = ["homebrew-mcp"]

    def get_system_prompt(self) -> str:
        return (
            "You are a macOS development environment specialist. "
            "Your job is to check Homebrew for outdated packages and assess each one. "
            "For each outdated package: classify the version jump (patch/minor/major), "
            "assess risk, and recommend action. Flag any brew doctor warnings. "
            "Be concise and specific. "
            "Always respond with valid JSON matching this shape:\n"
            '{"findings": [{"package": str, "current": str, "latest": str, '
            '"jump": "patch"|"minor"|"major"|"unknown", "detail": str}], '
            '"doctor_warnings": [str]}'
        )

    async def run(self, sessions: dict[str, ClientSession]) -> AgentResult:
        started_at = datetime.now(tz=timezone.utc)
        session = sessions["homebrew-mcp"]
        tool_calls: list[ToolCall] = []
        findings: list[Finding] = []

        # ── Step 1: list outdated ─────────────────────────────────────────────
        with ms_timer() as elapsed:
            outdated_result = await session.call_tool("list_outdated", {})
        tool_calls.append(ToolCall(tool="list_outdated", server="homebrew-mcp", duration_ms=elapsed[0], success=True))
        outdated = parse_tool_result(outdated_result)

        # ── Step 2: doctor status ─────────────────────────────────────────────
        with ms_timer() as elapsed:
            doctor_result = await session.call_tool("get_doctor_status", {})
        tool_calls.append(ToolCall(tool="get_doctor_status", server="homebrew-mcp", duration_ms=elapsed[0], success=True))
        doctor = parse_tool_result(doctor_result)

        # ── Step 3: Claude reasoning ──────────────────────────────────────────
        all_packages = outdated.get("formulae", []) + outdated.get("casks", [])
        user_content = (
            f"Outdated packages ({len(all_packages)} total):\n"
            + json.dumps(all_packages, indent=2)
            + f"\n\nBrew doctor healthy: {doctor.get('healthy')}\n"
            + f"Doctor warnings: {json.dumps(doctor.get('warnings', []))}"
        )

        with ms_timer() as elapsed:
            response = await _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": user_content}],
            )
        tool_calls.append(ToolCall(tool="messages.create", server="anthropic", duration_ms=elapsed[0], success=True))

        # ── Step 4: parse Claude response into Findings ───────────────────────
        try:
            parsed = json.loads(strip_fences(response.content[0].text))
        except json.JSONDecodeError:
            completed_at = datetime.now(tz=timezone.utc)
            return AgentResult(
                agent_name=self.name,
                agent_display_name=self.display_name,
                status=AgentStatus.error,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
                tool_calls=tool_calls,
                error=f"Failed to parse Claude response as JSON: {strip_fences(response.content[0].text)[:200]}",
            )

        now = datetime.now(tz=timezone.utc)

        for i, pkg in enumerate(parsed.get("findings", []), start=1):
            current = pkg.get("current", "?")
            latest = pkg.get("latest", "?")
            jump = classify(current, latest)
            if jump == "unknown":
                jump = pkg.get("jump", "unknown")
            severity = from_version_jump(jump)

            findings.append(Finding(
                id=f"brew-{i:03d}",
                source_agent=self.name,
                category="safe_upgrade" if severity == Severity.info else "outdated_package",
                severity=severity,
                title=f"{pkg.get('package', '?')}: {current} → {latest} ({jump})",
                detail=pkg.get("detail", ""),
                metadata={
                    "package": pkg.get("package"),
                    "current_version": current,
                    "latest_version": latest,
                    "version_jump": jump,
                    "source": "homebrew",
                },
                timestamp=now,
            ))

        for i, warning in enumerate(parsed.get("doctor_warnings", []), start=1):
            findings.append(Finding(
                id=f"brew-doc-{i:03d}",
                source_agent=self.name,
                category="doctor_warning",
                severity=Severity.warning,
                title=f"brew doctor: {warning[:60]}{'...' if len(warning) > 60 else ''}",
                detail=warning,
                metadata={"source": "brew_doctor"},
                timestamp=now,
            ))

        if not findings:
            findings.append(Finding(
                id="brew-000",
                source_agent=self.name,
                category="all_clear",
                severity=Severity.info,
                title="Homebrew is up to date",
                detail="No outdated packages and brew doctor reports no issues.",
                metadata={},
                timestamp=now,
            ))

        completed_at = datetime.now(tz=timezone.utc)
        result = AgentResult(
            agent_name=self.name,
            agent_display_name=self.display_name,
            status=AgentStatus.success,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            findings=findings,
            tool_calls=tool_calls,
        )
        result.compute_summary()
        return result
