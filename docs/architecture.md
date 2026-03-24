# Architecture

## Overview

```
CLI (cli.py)
  └─ Orchestrator (orchestrator.py)
       ├─ ServerManager (starts MCP servers, gives agents ClientSession objects)
       ├─ [Agent, Agent, Agent] (run in parallel via asyncio.gather)
       │    └─ BaseAgent.run() → AgentResult (list[Finding])
       ├─ find_cross_references() (correlates findings across agents)
       ├─ persist_briefing() (writes runs/brief-YYYY-MM-DD-HHMMSS.json)
       └─ BriefingOutput (the final contract, JSON to stdout)
```

## Components

### CLI (`morning_agents/cli.py`)

Typer app. Parses options, constructs agents, runs the orchestrator, renders output. Subcommands (`history`, `last`, `show`) use the persistence layer directly.

### Orchestrator (`morning_agents/orchestrator.py`)

Manages the full briefing lifecycle:

1. Determines which MCP servers are needed across all agents
2. Starts those servers via `ServerManager`
3. Runs agents in parallel (or serially with `--no-parallel`)
4. Calls `result.compute_summary()` on each `AgentResult`
5. Runs `find_cross_references()` on all results
6. Builds `BriefingOutput`
7. Persists to `runs/` (unless `persist=False`)

### ServerManager

Starts and shuts down MCP servers. Maps server names to `ClientSession` objects. Agents declare which servers they need via `mcp_servers = [...]`; the orchestrator deduplicates before starting.

Server configs live in `morning_agents/config.py` → `SERVER_REGISTRY`.

### Agents (`morning_agents/agents/`)

Each agent is a subclass of `BaseAgent`. Agents receive a dict of `ClientSession` objects keyed by server name. They call MCP tools, feed results to Claude, and return an `AgentResult`.

### Persistence (`morning_agents/persistence.py`)

Saves/loads briefing runs as JSON files in `runs/`. Files are named `brief-YYYY-MM-DD-HHMMSS.json`.

### Cross-Reference Engine (`morning_agents/skills/cross_reference.py`)

Rule-based correlation. Each `CorrelationRule` receives all `AgentResult` objects and returns `CrossReference` objects. Rules are registered in `CORRELATION_RULES`.

## Data Flow

```
MCP tool call → raw result
  → parse_tool_result() → dict
  → Claude (messages.create) → JSON string
  → strip_fences() + json.loads() → parsed dict
  → Finding objects
  → AgentResult
  → BriefingOutput (with cross_references + summary)
  → persist_briefing() → runs/brief-*.json
  → stdout (JSON) + stderr (Rich)
```

## Stdout vs Stderr

| Stream | Content | Why |
|---|---|---|
| stderr | Rich rendering, progress | Human-readable, doesn't pollute pipes |
| stdout | `BriefingOutput` JSON | Pipeable, scriptable |
