# Adding an Agent

Every agent follows the same pattern. Here's the complete recipe.

---

## Step 1: Write the Agent

Create `morning_agents/agents/my_agent.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone

import anthropic
from mcp import ClientSession

from morning_agents.agents.base import BaseAgent
from morning_agents.config import MODEL
from morning_agents.contracts.models import AgentResult, AgentStatus, Finding, Severity, ToolCall
from morning_agents.skills.mcp_utils import call_tool, parse_tool_result, strip_fences
from morning_agents.skills.timing import elapsed_ms, ms_timer

_client = anthropic.AsyncAnthropic()


class MyAgent(BaseAgent):
    name = "my_agent"
    display_name = "🔥 My Agent"
    mcp_servers = ["some-mcp"]          # must match SERVER_REGISTRY keys
    depends_on = []                     # optional: list of agent names to wait for
    workspace_type = "none"             # "none" | "scratch" | "persistent"

    def get_system_prompt(self) -> str:
        return (
            "You are a specialist. "
            "Always respond with valid JSON matching this shape:\n"
            '{"findings": [{"title": str, "detail": str, "severity": "info"|"warning"|"action_needed"}]}'
        )

    async def run(self, sessions: dict[str, ClientSession], upstream: dict | None = None) -> AgentResult:
        started_at = datetime.now(tz=timezone.utc)
        session = sessions["some-mcp"]
        tool_calls: list[ToolCall] = []
        findings: list[Finding] = []

        # 1. Call MCP tools
        with ms_timer() as elapsed:
            result = await call_tool(session, "some_tool", {})
        tool_calls.append(ToolCall(tool="some_tool", server="some-mcp", duration_ms=elapsed[0], success=True))

        data = parse_tool_result(result)

        # 2. Feed to Claude
        with ms_timer() as elapsed:
            response = await _client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=self.get_system_prompt(),
                messages=[{"role": "user", "content": json.dumps(data)}],
            )
        tool_calls.append(ToolCall(tool="messages.create", server="anthropic", duration_ms=elapsed[0], success=True))

        # 3. Parse findings
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
                error="Failed to parse Claude response",
            )

        now = datetime.now(tz=timezone.utc)

        for i, item in enumerate(parsed.get("findings", []), start=1):
            findings.append(Finding(
                id=f"my_agent-{i:03d}",
                source_agent=self.name,
                category="some_category",
                severity=Severity(item.get("severity", "info")),
                title=item.get("title", "?"),
                detail=item.get("detail", ""),
                metadata={"tool_id": "my_tool_id"},   # always include tool_id
                timestamp=now,
            ))

        if not findings:
            findings.append(Finding(
                id="my_agent-000",
                source_agent=self.name,
                category="all_clear",
                severity=Severity.info,
                title="Everything looks good",
                detail="No issues found.",
                metadata={"tool_id": "my_tool_id"},
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
```

---

## Step 2: Register the MCP Server

In `morning_agents/config.py`, add to `SERVER_REGISTRY`:

```python
SERVER_REGISTRY = {
    # ... existing entries ...
    "some-mcp": StdioServerParameters(
        command="bun",
        args=["run", str(Path(__file__).parent.parent / "mcp-servers" / "some-mcp" / "index.ts")],
    ),
}
```

---

## Step 3: Register the Agent in the CLI

In `morning_agents/cli.py`:

```python
from morning_agents.agents.my_agent import MyAgent

_AGENTS = {
    "brewmaster": BrewmasterAgent,
    "devenv": DevEnvAgent,
    "pr_queue": PRQueueAgent,
    "my_agent": MyAgent,    # add this
}
```

---

## Step 4: Use `tool_id` Consistently

The `tool_id` field in `Finding.metadata` is how cross-reference rules identify findings. Pick a stable, lowercase identifier and use it on every finding your agent emits.

```python
metadata={"tool_id": "my_tool_id", ...}
```

---

## Step 5: Write Evals

Add `evals/test_my_agent.py` following the pattern in `evals/test_brewmaster.py`. Unit tests (no network) go in `evals/test_*.py` and run with:

```bash
uv run pytest evals/ -v
```
