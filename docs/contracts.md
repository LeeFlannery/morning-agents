# Contracts

All Pydantic models live in `morning_agents/contracts/models.py`.

## Enums

### `Severity`

```python
class Severity(str, Enum):
    info = "info"
    warning = "warning"
    action_needed = "action_needed"
```

### `AgentStatus`

```python
class AgentStatus(str, Enum):
    success = "success"
    partial = "partial"
    error = "error"
```

---

## Core Models

### `Finding`

A single piece of intel from an agent.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID, e.g. `"brew-001"` |
| `source_agent` | `str` | Agent name that produced this |
| `category` | `str` | Free-form category tag |
| `severity` | `Severity` | `info` / `warning` / `action_needed` |
| `title` | `str` | One-line summary |
| `detail` | `str` | Longer description |
| `metadata` | `dict[str, Any]` | Agent-specific data (always include `tool_id`) |
| `timestamp` | `AwareDatetime` | UTC timestamp |

> **Convention:** Always include `tool_id` in `metadata`. Cross-reference rules key on it.

---

### `AgentResult`

One agent's complete output.

| Field | Type | Description |
|---|---|---|
| `agent_name` | `str` | Agent identifier |
| `agent_display_name` | `str` | Display string with emoji |
| `status` | `AgentStatus` | Success / partial / error |
| `started_at` | `AwareDatetime` | When the agent started |
| `completed_at` | `AwareDatetime` | When it finished |
| `duration_ms` | `int` | Wall time in milliseconds |
| `findings` | `list[Finding]` | All findings |
| `summary` | `FindingSummary \| None` | Computed by `compute_summary()` |
| `tool_calls` | `list[ToolCall]` | MCP and API calls made |
| `error` | `str \| None` | Error message if status is error |

`compute_summary()` is called by the orchestrator after `agent.run()` returns.

---

### `CrossReference`

A correlation between findings from different agents.

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Unique ID, e.g. `"xref-node-pr-abc12345"` |
| `severity` | `Severity` | Severity of the correlation |
| `title` | `str` | One-line description |
| `detail` | `str` | Full explanation |
| `source_findings` | `list[str]` | Finding IDs that triggered this |
| `source_agents` | `list[str]` | Agent names involved |
| `timestamp` | `AwareDatetime` | When the cross-reference was generated |

---

### `BriefingOutput`

The top-level output contract. Everything else is nested here.

| Field | Type | Description |
|---|---|---|
| `version` | `str` | App version |
| `briefing_id` | `str` | e.g. `"brief-2026-03-23-091500"` |
| `generated_at` | `AwareDatetime` | UTC timestamp |
| `duration_ms` | `int` | Total wall time |
| `agent_results` | `list[AgentResult]` | One per agent |
| `cross_references` | `list[CrossReference]` | Correlated findings |
| `summary` | `BriefingSummary` | Counts and stats |
| `config` | `BriefingConfig` | Runtime config snapshot |

---

### Supporting Models

**`ToolCall`** — records a single MCP tool or API call:

```python
class ToolCall(BaseModel):
    tool: str         # tool name
    server: str       # "homebrew-mcp", "anthropic", etc.
    duration_ms: int
    success: bool
```

**`FindingSummary`** — per-agent finding counts:

```python
class FindingSummary(BaseModel):
    total: int
    by_severity: dict[str, int]
```

**`BriefingSummary`** — briefing-level stats:

```python
class BriefingSummary(BaseModel):
    agents_run: int
    agents_succeeded: int
    agents_failed: int
    total_findings: int
    by_severity: dict[str, int]
    mcp_servers_used: int
```
