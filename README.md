# Morning Agents

A CLI tool that runs agents every morning and prints a terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and your day ahead.

---

## What's here (Session 1)

### TS/Python MCP bridge (spike)

The core architecture is a Python orchestrator that spawns TypeScript MCP servers as child processes and communicates over stdio. `spike_test.py` proves this works.

```
Python orchestrator
    └── stdio → TypeScript MCP server (Bun)
                    └── shell commands, APIs, etc.
```

### homebrew-mcp

An MCP server (`mcp-servers/homebrew-mcp/index.ts`) that wraps the `brew` CLI.

| Tool | What it does |
|------|-------------|
| `list_outdated` | All outdated formulae and casks with current/latest versions |
| `get_package_info` | Details on a specific package (version, desc, deps) |
| `get_doctor_status` | Runs `brew doctor`, returns health status and warnings |

### Pydantic contracts

All data shapes are defined in `morning_agents/contracts/models.py`. Every agent produces `Finding` objects, collected into an `AgentResult`. The orchestrator combines results into a `BriefingOutput`.

```
BriefingOutput
├── AgentResult (one per agent)
│   └── Finding[] (id, severity, title, detail, metadata)
└── CrossReference[] (orchestrator-generated)
```

Severity levels: `info` (green) · `warning` (yellow) · `action_needed` (red)

---

## Project structure

```
morning-agents/
├── mcp-servers/
│   ├── homebrew-mcp/index.ts   # Homebrew connector
│   ├── spike/index.ts          # Bridge spike
│   └── package.json            # Bun dependencies
├── morning_agents/
│   └── contracts/
│       └── models.py           # Pydantic models (Finding, AgentResult, etc.)
├── evals/
│   └── test_homebrew_mcp.py    # Integration tests for homebrew-mcp
├── spike_test.py               # TS/Python bridge proof
├── pyproject.toml              # Python config + dependencies
└── .python-version             # 3.13.12 (pyenv)
```

---

## Setup

**Requirements:** Python 3.13+ (pyenv), uv, Bun, Homebrew

```bash
# Python deps
uv sync --dev

# TypeScript MCP servers
cd mcp-servers && bun install
```

## Running the spike

```bash
uv run python spike_test.py
```

## Running homebrew-mcp tests

```bash
uv run python evals/test_homebrew_mcp.py
```

---

## Where it's going

### Session 2 - Brewmaster agent
The first agent. Calls homebrew-mcp tools, classifies version bumps (patch/minor/major), and produces structured `Finding` objects with severity labels.

### Session 3 - CLI + orchestrator
`morning-agents` as a runnable command. Starts the MCP server, runs the Brewmaster agent, and renders output in the terminal with Rich.

### Session 4 - devenv-mcp + DevEnv agent
A second MCP server checking Xcode, VS Code, Node, and Python versions against latest. Runs alongside Brewmaster concurrently.

### Session 5 - Community MCPs + PR Queue + Day Ahead
GitHub (PR review queue), Google Calendar, and Gmail via community MCP servers. Two more agents.

### Session 6 - Cross-references + polish
Correlates findings across agents, adds run persistence to `runs/`, and adds `--quiet`, `--json`, and `--no-persist` flags.

### Session 7 - Evals + governance
Eval suite with an LLM judge, read-only scope enforcement, max tool call limits, and execution logging.

### Session 8 - README + publish
Architecture diagrams, final docs, public release.
