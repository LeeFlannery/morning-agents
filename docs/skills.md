# Skills

Shared utilities in `morning_agents/skills/`.

---

## `mcp_utils.py`

Helpers for working with MCP tool results.

### `call_tool(session, tool_name, args) → CallToolResult`

Calls an MCP tool and returns the raw result.

```python
result = await call_tool(session, "list_outdated_packages", {})
```

### `parse_tool_result(result) → dict | list | str`

Extracts and parses the content from a `CallToolResult`. Handles JSON strings automatically.

### `strip_fences(text) → str`

Strips markdown code fences from a string (e.g. ` ```json ... ``` `). Use before `json.loads()` on Claude responses.

---

## `semver.py`

Version classification.

### `classify(current, latest) → str`

Returns `"patch"`, `"minor"`, `"major"`, `"current"`, or `"unknown"` based on semver comparison.

```python
classify("20.0.0", "22.0.0")  # "major"
classify("1.2.3", "1.2.4")    # "patch"
classify("1.2.3", "1.2.3")    # "current"
```

---

## `severity.py`

### `from_version_jump(jump) → Severity`

Maps a version jump string to a `Severity` value.

| Jump | Severity |
|---|---|
| `"major"` | `action_needed` |
| `"minor"` | `warning` |
| `"patch"` | `info` |
| `"current"` | `info` |
| `"unknown"` | `warning` |
| `"not_installed"` | `warning` |

---

## `time_context.py`

### `relative_time(dt) → str`

Returns a human-friendly relative time string.

```python
relative_time(three_days_ago)   # "3 days ago"
relative_time(two_hours_ago)    # "2 hours ago"
relative_time(just_now)         # "just now"
```

---

## `timing.py`

### `elapsed_ms(start, end) → int`

Returns milliseconds between two `datetime` objects.

### `ms_timer() → context manager`

Context manager that captures elapsed time into a list (so it can be read after the block).

```python
with ms_timer() as elapsed:
    result = await some_async_call()
duration = elapsed[0]  # ms
```

---

## `cross_reference.py`

The correlation rule engine. See [Architecture](architecture.md) for how it fits in.

### `CorrelationRule` (ABC)

Implement `apply(results: list[AgentResult]) -> list[CrossReference]` to add a new rule.

### `NodeUpgradeVsPRRule`

Fires when DevEnv detects a Node.js upgrade AND PRQueue has a Node-related PR open. Emits a `warning` cross-reference recommending coordination.

**Triggered by:**
- A finding with `tool_id == "node"` and severity `warning` or `action_needed`
- A finding with `tool_id == "github_pr"` whose title contains `node`, `nodejs`, `node.js`, `npm`, or `nvm`

### `CORRELATION_RULES`

The list of active rules. Add new `CorrelationRule` instances here to activate them.

### `find_cross_references(results) → list[CrossReference]`

Runs all `CORRELATION_RULES` against the full result set and returns the combined list.
