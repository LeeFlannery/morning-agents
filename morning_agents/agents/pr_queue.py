from __future__ import annotations

import asyncio
import json
import os
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
from morning_agents.skills.mcp_utils import call_tool, strip_fences
from morning_agents.skills.time_context import relative_time
from morning_agents.skills.timing import elapsed_ms, ms_timer

_client = anthropic.AsyncAnthropic()

_JUMP_TO_SEVERITY = {
    "action": Severity.action_needed,
    "warning": Severity.warning,
    "info": Severity.info,
}

GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME", "")


class PRQueueAgent(BaseAgent):
    name = "pr_queue"
    display_name = "🔀 PR Queue"
    mcp_servers = ["github-mcp"]

    def get_system_prompt(self) -> str:
        return (
            "You are a GitHub pull request triage specialist. "
            "Your job is to analyze pull requests and determine what needs immediate attention. "
            "For PRs awaiting your review: flag if they're urgent, stale, or have CI failures. "
            "For your own open PRs: flag if they need a response to review comments, have failing CI, "
            "or have been open too long without merge. "
            "Be concise and actionable. "
            "Always respond with valid JSON matching this shape:\n"
            '{"findings": [{"pr_id": str, "repo": str, "title": str, '
            '"severity": "action"|"warning"|"info", '
            '"detail": str, "url": str}]}'
        )

    async def run(self, sessions: dict[str, ClientSession], upstream: dict | None = None) -> AgentResult:
        started_at = datetime.now(tz=timezone.utc)
        session = sessions["github-mcp"]
        tool_calls: list[ToolCall] = []
        findings: list[Finding] = []

        # ── Step 1: discover available tools ─────────────────────────────────
        tools_result = await session.list_tools()
        available_tools = {t.name for t in tools_result.tools}

        # ── Step 2: search for PRs needing review + own open PRs ─────────────
        review_query = f"is:pr is:open review-requested:{GITHUB_USERNAME}" if GITHUB_USERNAME else "is:pr is:open"
        author_query = f"is:pr is:open author:{GITHUB_USERNAME}" if GITHUB_USERNAME else "is:pr is:open"

        review_result = None
        author_result = None

        if "search_pull_requests" in available_tools:
            with ms_timer() as elapsed:
                review_result, author_result = await asyncio.gather(
                    call_tool(session, "search_pull_requests", {"query": review_query, "perPage": 20}),
                    call_tool(session, "search_pull_requests", {"query": author_query, "perPage": 20}),
                )
            tool_calls.append(ToolCall(
                tool="search_pull_requests",
                server="github-mcp",
                duration_ms=elapsed[0],
                success=True,
            ))
            tool_calls.append(ToolCall(
                tool="search_pull_requests",
                server="github-mcp",
                duration_ms=elapsed[0],
                success=True,
            ))

        # Parse raw results — the github-mcp server returns content as text
        def _parse_search(result) -> list[dict]:
            if result is None:
                return []
            try:
                text = result.content[0].text
                data = json.loads(strip_fences(text))
                if isinstance(data, list):
                    return data
                # GitHub search returns {"total_count": N, "items": [...]}
                return data.get("items", [])
            except Exception:
                return []

        review_prs = _parse_search(review_result)
        author_prs = _parse_search(author_result)

        # Deduplicate by PR number+repo
        seen: set[str] = set()
        all_prs: list[dict] = []
        for pr in review_prs + author_prs:
            key = f"{pr.get('number', '')}:{pr.get('repository_url', pr.get('html_url', ''))}"
            if key not in seen:
                seen.add(key)
                all_prs.append(pr)

        # All-clear case
        if not all_prs:
            now = datetime.now(tz=timezone.utc)
            findings.append(Finding(
                id="pr-000",
                source_agent=self.name,
                category="all_clear",
                severity=Severity.info,
                title="No PRs need your attention",
                detail="No PRs awaiting review and no open PRs authored by you.",
                metadata={"tool_id": "github_pr"},
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
                tool_calls=tool_calls,
            )

        # ── Step 3: enrich PR data with relative timestamps ───────────────────
        enriched = []
        for pr in all_prs:
            entry = dict(pr)
            # Add relative time for created_at / updated_at
            for field in ("created_at", "updated_at"):
                val = pr.get(field)
                if val:
                    try:
                        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        entry[f"{field}_relative"] = relative_time(dt)
                    except Exception:
                        pass
            enriched.append(entry)

        # ── Step 4: Claude reasoning ──────────────────────────────────────────
        review_ids = {pr.get("number") for pr in review_prs}
        user_content = (
            f"GitHub username: {GITHUB_USERNAME}\n\n"
            f"PRs awaiting your review ({len(review_prs)}):\n"
            + json.dumps([p for p in enriched if p.get("number") in review_ids], indent=2)
            + f"\n\nYour open PRs ({len(author_prs)}):\n"
            + json.dumps([p for p in enriched if p.get("number") not in review_ids], indent=2)
        )

        with ms_timer() as elapsed:
            response = await _client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": user_content}],
            )
        tool_calls.append(ToolCall(
            tool="messages.create",
            server="anthropic",
            duration_ms=elapsed[0],
            success=True,
        ))

        # ── Step 5: parse Claude response into Findings ───────────────────────
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
            raw_sev = item.get("severity", "info")
            severity = _JUMP_TO_SEVERITY.get(raw_sev, Severity.info)

            findings.append(Finding(
                id=f"pr-{i:03d}",
                source_agent=self.name,
                category="pr_review" if severity == Severity.action_needed else "pr_update",
                severity=severity,
                title=f"{item.get('repo', '?')}#{item.get('pr_id', '?')}: {item.get('title', '?')}",
                detail=item.get("detail", ""),
                metadata={
                    "tool_id": "github_pr",
                    "pr_id": item.get("pr_id"),
                    "repo": item.get("repo"),
                    "url": item.get("url"),
                    "source": "github",
                },
                timestamp=now,
            ))

        if not findings:
            findings.append(Finding(
                id="pr-000",
                source_agent=self.name,
                category="all_clear",
                severity=Severity.info,
                title="No PRs need your attention",
                detail="All PRs are in good shape.",
                metadata={"tool_id": "github_pr"},
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
            tool_calls=tool_calls,
        )
