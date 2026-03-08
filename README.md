# Morning Agents

A CLI tool that runs a set of AI agents every morning and gives you a terminal briefing — Homebrew health, dev tool versions, GitHub PRs, and your day ahead.

---

## What's here (Session 1)

### TS↔Python MCP bridge (spike)

The core architecture is a Python orchestrator that spawns TypeScript MCP servers as child processes and talks to them over stdio. `spike_test.py` proves this works end to end.

```
Python orchestrator
    └── stdio → TypeScript MCP server (Bun)
                    └── shell commands, APIs, etc.
```

### homebrew-mcp

A custom MCP server (`mcp-servers/homebrew-mcp/index.ts`) that wraps the `brew` CLI.

| Tool | What it does |
|------|-------------|
| `list_outdated` | All outdated formulae and casks with current/latest versions |
| `get_package_info` | Details on a specific package (version, desc, deps) |
| `get_doctor_status` | Runs `brew doctor`, returns health status and warnings |

### Pydantic contracts

All data shapes are defined in `src/contracts/models.py`. Every agent produces `Finding` objects, collected into an `AgentResult`. The orchestrator combines all results into a `BriefingOutput`.

```
BriefingOutput
├── AgentResult (one per agent)
│   └── Finding[] (atomic unit — id, severity, title, detail, metadata)
└── CrossReference[] (orchestrator-generated correlations)
```

Severity levels: `info` (green) · `warning` (yellow) · `action_needed` (red)

---

## Project structure

```
morning-agents/
├── mcp-servers/
│   ├── homebrew-mcp/index.ts   # Homebrew connector
│   ├── spike/index.ts          # Hello-world bridge spike
│   └── package.json            # Bun dependencies
├── src/
│   └── contracts/
│       └── models.py           # Pydantic models (Finding, AgentResult, etc.)
├── evals/
│   └── test_homebrew_mcp.py    # Integration tests for homebrew-mcp
├── spike_test.py               # TS↔Python bridge proof
├── pyproject.toml              # Python config + dependencies
└── .python-version             # 3.13.12 (pyenv)
```

---

## Setup

**Requirements:** Python 3.13+ (pyenv), Bun, Homebrew

```bash
# Python
pyenv install 3.13.12
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# TypeScript MCP servers
cd mcp-servers
bun install
```

## Running the spike

```bash
python spike_test.py
```

## Running homebrew-mcp tests

```bash
python evals/test_homebrew_mcp.py
```

---

## Where it's going

### Session 2 — Brewmaster agent
The first real agent. Uses Claude's tool_use API to reason over homebrew-mcp output, classify version bumps (patch/minor/major via semver), and produce structured `Finding` objects with appropriate severity.

### Session 3 — CLI + orchestrator
`morning-agents` as a runnable CLI command. Starts the MCP server, runs the Brewmaster agent, renders output in the terminal with Rich (color, tables, severity indicators).

### Session 4 — devenv-mcp + DevEnv agent
A second custom MCP server checking Xcode, VS Code, Node, and Python versions against latest. A second agent runs alongside Brewmaster concurrently.

### Session 5 — Community MCPs + PR Queue + Day Ahead
Connects to community MCP servers for GitHub (PR review queue), Google Calendar, and Gmail. Two more agents: one for PRs, one for your day ahead.

### Session 6 — Cross-references + polish
The orchestrator correlates findings across agents (meeting with someone + unread email from them = flagged). Adds run persistence to `runs/`, `--quiet`, `--json`, and `--no-persist` flags.

### Session 7 — Evals + governance
LLM-as-judge eval suite, scope constraints (read-only enforcement, max tool call limits), and execution logging.

### Session 8 — README + publish
Architecture diagrams, final docs, public release.
