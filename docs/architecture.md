# Architecture

## Overview

```
CLI (cli.py)
  └─ Orchestrator (orchestrator/)
       ├─ ServerManager          starts MCP servers, holds ClientSession objects
       ├─ ResourceContext        semaphore + workspace root + briefing ID
       ├─ execute_dag()          topological execution via graphlib.TopologicalSorter
       │    ├─ depth 0: [BrewmasterAgent, DevEnvAgent, PRQueueAgent]  (concurrent)
       │    └─ depth 1: [CrossRefAgent]  (receives depth-0 results as upstream)
       ├─ persist_briefing()     writes runs/brief-YYYY-MM-DD-HHMMSS.json
       └─ BriefingOutput         final contract, JSON to stdout
```

## Components

### CLI (`morning_agents/cli.py`)

Typer app. Parses options, constructs agent classes, runs the orchestrator, renders output. Subcommands (`history`, `last`, `show`) use the persistence layer directly.

### Orchestrator (`morning_agents/orchestrator/`)

The orchestrator package has four modules:

| Module | Responsibility |
|---|---|
| `orchestrator.py` | Briefing lifecycle: setup, DAG execution, result assembly, persist |
| `dag_executor.py` | `execute_dag()` — topological sort, concurrency, failure isolation |
| `server_manager.py` | MCP server process lifecycle, `ClientSession` management |
| `resources.py` | `ResourceContext` dataclass injected into every agent |

**DAG execution flow:**

1. Build dependency graph from each agent's `depends_on`
2. Dependencies are *soft*: if a declared dependency is not in the active agent set, it is silently ignored rather than erroring (supports partial runs)
3. `TopologicalSorter.get_ready()` yields each tier of agents that have no remaining unfinished dependencies
4. Each tier runs concurrently via `asyncio.gather`
5. Failed agents cascade: dependents are skipped and marked as errors, but independent agents still run
6. Each `run()` call is gated by a shared `asyncio.Semaphore` (default: 4) to prevent rate-limit hammering on the Anthropic API

### ResourceContext (`morning_agents/orchestrator/resources.py`)

Frozen dataclass injected into every agent at construction time. Holds:

- `semaphore` — shared concurrency gate for API calls
- `workspace_root` — base path for per-run agent workspaces (`runs/`)
- `briefing_id` — current run ID (used to namespace workspaces)
- `server_manager` — reference for agents that need direct session access

Agents with `workspace_type = "scratch"` or `"persistent"` call `self.workspace` to get their isolated `runs/<briefing_id>/<agent_name>/` directory.

### BaseAgent (`morning_agents/agents/base.py`)

Abstract base class. Subclasses must define three class attributes:

```python
class MyAgent(BaseAgent):
    name = "my_agent"                  # unique key, used in depends_on
    display_name = "My Agent"          # shown in terminal output
    mcp_servers = ["some-mcp"]         # servers this agent needs

    # Optional:
    depends_on = ["other_agent"]       # upstream agents (default: [])
    workspace_type = "scratch"         # "none" | "scratch" | "persistent"

    async def run(
        self,
        sessions: dict[str, ClientSession],
        upstream: dict[str, AgentResult] | None = None,
    ) -> AgentResult: ...
```

`upstream` is `None` for depth-0 agents, and `{agent_name: AgentResult}` for agents that declared `depends_on`.

### ServerManager (`morning_agents/orchestrator/server_manager.py`)

Starts and shuts down MCP servers as child processes over stdio. Deduplicates: if multiple agents need the same server, it starts once and shares the `ClientSession`. Server configs live in `config.py → SERVER_REGISTRY`.

### Persistence (`morning_agents/persistence.py`)

Saves/loads briefing runs as JSON files in `runs/`. Files are named `brief-YYYY-MM-DD-HHMMSS.json`.

### Cross-Reference Engine (`morning_agents/skills/cross_reference.py`)

Rule-based correlation. Each `CorrelationRule` receives all `AgentResult` objects and returns `CrossReference` objects. Rules are registered in `CORRELATION_RULES`. The `CrossRefAgent` wraps this engine as a proper DAG node with `depends_on = ["brewmaster", "devenv", "pr_queue"]`.

## Data Flow

```
MCP tool call → raw result
  → parse_tool_result() → dict
  → Claude (messages.create) → JSON string
  → strip_fences() + json.loads() → parsed dict
  → Finding objects
  → AgentResult
  → DAG executor collects all AgentResults
  → CrossRefAgent correlates findings (depth 1)
  → BriefingOutput (agent_results + cross_references + execution metadata)
  → persist_briefing() → runs/brief-*.json
  → stdout (JSON) + stderr (Rich)
```

## ExecutionMeta

Every `BriefingOutput` now includes an `execution` field:

```json
{
  "execution": {
    "stages": [["brewmaster", "devenv", "pr_queue"], ["cross_ref"]],
    "dependency_graph": {
      "brewmaster": [],
      "devenv": [],
      "pr_queue": [],
      "cross_ref": ["brewmaster", "devenv", "pr_queue"]
    },
    "retries": {}
  }
}
```

This makes the execution topology inspectable without needing to understand the source.

## Stdout vs Stderr

| Stream | Content | Why |
|---|---|---|
| stderr | Rich rendering, progress | Human-readable, doesn't pollute pipes |
| stdout | `BriefingOutput` JSON | Pipeable, scriptable |
