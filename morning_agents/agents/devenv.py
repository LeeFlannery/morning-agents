from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import anthropic
from mcp import ClientSession

from morning_agents.agents.base import BaseAgent
from morning_agents.config import MODEL
from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    Finding,
    Severity,
    ToolCall,
)
from morning_agents.skills.mcp_utils import call_tool, parse_tool_result, strip_fences
from morning_agents.skills.semver import classify
from morning_agents.skills.severity import from_version_jump
from morning_agents.skills.timing import elapsed_ms, ms_timer

_client = anthropic.AsyncAnthropic()


class DevEnvAgent(BaseAgent):
    name = "devenv"
    display_name = "🛠️  DevEnv"
    mcp_servers = ["devenv-mcp"]

    def get_system_prompt(self) -> str:
        return (
            "You are a macOS development environment specialist. "
            "Your job is to check installed dev tool versions against latest available versions. "
            "For each tool: classify the version jump (patch/minor/major/current/unknown), "
            "assess impact, and recommend action if an update is needed. "
            "Be concise and specific. "
            "Always respond with valid JSON matching this shape:\n"
            '{"findings": [{"tool": str, "installed": str, "latest": str, '
            '"jump": "patch"|"minor"|"major"|"current"|"unknown"|"not_installed", '
            '"detail": str}]}'
        )

    async def run(self, sessions: dict[str, ClientSession]) -> AgentResult:
        started_at = datetime.now(tz=timezone.utc)
        session = sessions["devenv-mcp"]
        tool_calls: list[ToolCall] = []
        findings: list[Finding] = []

        # ── Step 1: fetch all version checks concurrently ─────────────────────
        with ms_timer() as elapsed:
            xcode_result, vscode_result, node_result, python_result = await asyncio.gather(
                call_tool(session, "check_xcode_version", {}),
                call_tool(session, "check_vscode_version", {}),
                call_tool(session, "check_node_version", {}),
                call_tool(session, "check_python_version", {}),
            )
        for tool_name in ("check_xcode_version", "check_vscode_version", "check_node_version", "check_python_version"):
            tool_calls.append(ToolCall(tool=tool_name, server="devenv-mcp", duration_ms=elapsed[0], success=True))

        xcode = parse_tool_result(xcode_result)
        vscode = parse_tool_result(vscode_result)
        node = parse_tool_result(node_result)
        python = parse_tool_result(python_result)

        # ── Step 2: Claude reasoning ──────────────────────────────────────────
        user_content = (
            "Dev tool versions:\n"
            + json.dumps({
                "xcode": xcode,
                "vscode": vscode,
                "node": node,
                "python": python,
            }, indent=2)
        )

        with ms_timer() as elapsed:
            response = await _client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": user_content}],
            )
        tool_calls.append(ToolCall(tool="messages.create", server="anthropic", duration_ms=elapsed[0], success=True))

        # ── Step 3: parse Claude response into Findings ───────────────────────
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
                duration_ms=elapsed_ms(started_at, completed_at),
                tool_calls=tool_calls,
                error=f"Failed to parse Claude response as JSON: {strip_fences(response.content[0].text)[:200]}",
            )

        now = datetime.now(tz=timezone.utc)

        for i, item in enumerate(parsed.get("findings", []), start=1):
            tool_name = item.get("tool", "?")
            installed = item.get("installed", "?")
            latest = item.get("latest", "?")
            jump = item.get("jump", "unknown")

            if installed == "not_installed":
                severity = Severity.warning
                category = "not_installed"
            else:
                # Local semver is authoritative; Claude's jump is the fallback
                local = classify(installed, latest)
                if local != "unknown":
                    jump = local
                severity = from_version_jump(jump)
                category = "safe_upgrade" if severity == Severity.info else "outdated_tool"

            findings.append(Finding(
                id=f"devenv-{i:03d}",
                source_agent=self.name,
                category=category,
                severity=severity,
                title=f"{tool_name}: {installed} → {latest} ({jump})" if installed != "not_installed" else f"{tool_name}: not installed",
                detail=item.get("detail", ""),
                metadata={
                    "tool": tool_name,
                    "installed_version": installed,
                    "latest_version": latest,
                    "version_jump": jump,
                    "source": "devenv",
                },
                timestamp=now,
            ))

        if not findings:
            findings.append(Finding(
                id="devenv-000",
                source_agent=self.name,
                category="all_clear",
                severity=Severity.info,
                title="Dev environment is up to date",
                detail="All checked tools are current.",
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
            duration_ms=elapsed_ms(started_at, completed_at),
            findings=findings,
            tool_calls=tool_calls,
        )
        result.compute_summary()
        return result
