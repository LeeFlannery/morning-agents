# Morning Agents

A CLI tool that runs agents every morning and prints a terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and your day ahead.

Python is the brains. TypeScript/Bun is the hands.

---

## What's here (Sessions 1-3)

### Architecture

A Python orchestrator spawns TypeScript MCP servers as child processes over stdio. Each agent declares which servers it needs; the orchestrator starts them concurrently and hands off connected sessions.

```
morning-agents (Python CLI)
    └── Orchestrator
            ├── ServerManager  ←→  stdio  ←→  homebrew-mcp (Bun)
            └── BrewmasterAgent → Finding[]
```

### homebrew-mcp

A TypeScript MCP server (`mcp-servers/homebrew-mcp/index.ts`) that wraps the `brew` CLI.

| Tool | What it does |
|------|-------------|
| `list_outdated` | All outdated formulae and casks with current/latest versions |
| `get_package_info` | Details on a specific package (version, desc, deps) |
| `get_doctor_status` | Runs `brew doctor`, returns health status and warnings |

### Brewmaster agent

Calls homebrew-mcp tools concurrently, sends results to Claude for analysis, classifies version jumps (patch/minor/major), and produces structured `Finding` objects with severity labels.

### Orchestrator

Manages the full briefing lifecycle: start servers, run agents in parallel, assemble `BriefingOutput`, tear down servers. Each agent run has a 120s timeout and full error isolation — one agent failing doesn't affect others.

### Pydantic contracts

All data shapes live in `morning_agents/contracts/models.py`. Every agent produces `Finding` objects, collected into `AgentResult`. The orchestrator combines results into `BriefingOutput`.

```
BriefingOutput
├── AgentResult (one per agent)
│   └── Finding[] (id, severity, title, detail, metadata)
└── CrossReference[] (session 6)
```

Severity levels: `info` (green) · `warning` (yellow) · `action_needed` (red)

---

## Project structure

```
morning-agents/
├── mcp-servers/
│   └── homebrew-mcp/index.ts   # Homebrew MCP server (Bun)
├── morning_agents/
│   ├── agents/
│   │   ├── base.py             # BaseAgent ABC
│   │   └── brewmaster.py       # Homebrew agent
│   ├── contracts/
│   │   └── models.py           # Pydantic models (Finding, AgentResult, etc.)
│   ├── skills/
│   │   ├── mcp_utils.py        # call_tool, parse_tool_result, strip_fences
│   │   ├── semver.py           # Version jump classification
│   │   ├── severity.py         # Severity mapping
│   │   └── timing.py           # ms_timer, elapsed_ms
│   ├── cli.py                  # Typer CLI + Rich renderer
│   ├── config.py               # SERVER_REGISTRY, MODEL, VERSION
│   └── orchestrator.py         # ServerManager + Orchestrator
├── evals/
│   ├── test_brewmaster.py      # Brewmaster integration tests
│   └── test_orchestrator.py    # Orchestrator integration tests
├── pyproject.toml
└── .python-version             # 3.13.12
```

---

## Setup

**Requirements:** Python 3.13+, uv, Bun, Homebrew

```bash
# Python deps
uv sync --dev

# TypeScript MCP servers
cd mcp-servers && bun install
```

## Running

```bash
# Needs ANTHROPIC_API_KEY — use 1Password or export directly
op run --env-file=op.env -- uv run morning-agents

# Options
morning-agents --help
morning-agents --quiet          # titles only, no detail lines
morning-agents --json           # raw BriefingOutput JSON
morning-agents --no-parallel    # run agents sequentially
```

## Tests

```bash
op run --env-file=op.env -- uv run pytest
```

---

## Where it's going

### Session 4 - devenv-mcp + DevEnv agent
A second MCP server checking Xcode, VS Code, Node, and Python versions against latest. Runs alongside Brewmaster concurrently.

### Session 5 - Community MCPs + PR Queue + Day Ahead
GitHub (PR review queue), Google Calendar, and Gmail via community MCP servers. Two more agents.

### Session 6 - Cross-references + polish
Correlates findings across agents (e.g., a major Node upgrade flagged by both devenv and a GitHub PR). Adds run persistence to `runs/`.

### Session 7 - Evals + governance
Eval suite with an LLM judge, read-only scope enforcement, max tool call limits, and execution logging.

### Session 8 - README + publish
Architecture diagrams, final docs, public release.
