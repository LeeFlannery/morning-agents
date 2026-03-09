# Morning Agents

A CLI tool that runs agents every morning and prints a terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and your day ahead.

Python is the brains. TypeScript/Bun is the hands.

---

## What's here (Sessions 1-4)

### Architecture

A Python orchestrator spawns TypeScript MCP servers as child processes over stdio. Each agent declares which servers it needs; the orchestrator starts them concurrently and hands off connected sessions.

```
morning-agents (Python CLI)
    └── Orchestrator
            ├── ServerManager  ←→  stdio  ←→  homebrew-mcp (Bun)
            │                                  devenv-mcp (Bun)
            ├── BrewmasterAgent → Finding[]
            └── DevEnvAgent     → Finding[]
```

Both agents run concurrently by default. Adding a new agent requires only a new agent file — the orchestrator, renderer, and CLI are agent-agnostic.

### homebrew-mcp

A TypeScript MCP server (`mcp-servers/homebrew-mcp/index.ts`) that wraps the `brew` CLI.

| Tool | What it does |
|------|-------------|
| `list_outdated` | All outdated formulae and casks with current/latest versions |
| `get_package_info` | Details on a specific package (version, desc, deps) |
| `get_doctor_status` | Runs `brew doctor`, returns health status and warnings |

### devenv-mcp

A TypeScript MCP server (`mcp-servers/devenv-mcp/index.ts`) that checks dev tool versions against their latest releases.

| Tool | What it does |
|------|-------------|
| `check_xcode_version` | Installed vs latest Xcode; CLI Tools status |
| `check_vscode_version` | Installed vs latest VS Code |
| `check_node_version` | Installed vs latest LTS Node.js |
| `check_python_version` | Installed vs latest Python 3 |

Each tool runs a local `spawn` call and a version API fetch concurrently. Gracefully handles tools that are not installed.

### Brewmaster agent

Calls homebrew-mcp tools concurrently, sends results to Claude for analysis, classifies version jumps (patch/minor/major), and produces structured `Finding` objects with severity labels.

### DevEnv agent

Calls all four devenv-mcp tools concurrently, sends results to Claude for analysis, classifies version jumps, and produces `Finding` objects. The local semver classifier is authoritative; Claude's value is the fallback for non-semver version strings.

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
│   ├── homebrew-mcp/index.ts   # Homebrew MCP server (Bun)
│   └── devenv-mcp/index.ts     # Dev tool version checker (Bun)
├── morning_agents/
│   ├── agents/
│   │   ├── base.py             # BaseAgent ABC
│   │   ├── brewmaster.py       # Homebrew agent
│   │   └── devenv.py           # Dev tool versions agent
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
│   ├── test_devenv.py          # DevEnv integration tests
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
morning-agents --quiet              # titles only, no detail lines
morning-agents --no-parallel        # run agents sequentially
morning-agents -a brewmaster        # run a specific agent (repeat for multiple)
morning-agents -a brewmaster -a devenv  # run both explicitly

# JSON output is always written to stdout. Capture or redirect as needed:
op run --env-file=op.env -- uv run morning-agents > briefing.json
```

## Tests

```bash
op run --env-file=op.env -- uv run pytest evals/ -v
```

---

## Where it's going

### ~~Session 4 - devenv-mcp + DevEnv agent~~ (complete)
Second MCP server checking Xcode, VS Code, Node, and Python versions against latest. Runs alongside Brewmaster concurrently. Both agents are now the default.

### Session 5 - Community MCPs + PR Queue + Day Ahead
GitHub (PR review queue), Google Calendar, and Gmail via community MCP servers. Two more agents.

### Session 6 - Cross-references + polish
Correlates findings across agents (e.g., a major Node upgrade flagged by both devenv and a GitHub PR). Adds run persistence to `runs/`.

### Session 7 - Evals + governance
Eval suite with an LLM judge, read-only scope enforcement, max tool call limits, and execution logging.

### Session 8 - Architecture diagrams + polish
Architecture diagrams, eval suite hardening, and final cleanup.
