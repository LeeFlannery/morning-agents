# Morning Agents

A CLI tool that runs agents every morning and prints a terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and your day ahead.

Python is the brains. TypeScript/Bun is the hands. Third-party Go binaries are welcome too.

---

## What's here (Sessions 1-5)

### Architecture

A Python orchestrator spawns MCP servers as child processes over stdio. Each agent declares which servers it needs; the orchestrator starts them concurrently and hands off connected sessions.

```
morning-agents (Python CLI)
    └── Orchestrator
            ├── ServerManager  ←→  stdio  ←→  homebrew-mcp (Bun/TS)
            │                  ←→  stdio  ←→  devenv-mcp (Bun/TS)
            │                  ←→  stdio  ←→  github-mcp-server (Go binary)
            ├── BrewmasterAgent → Finding[]
            ├── DevEnvAgent     → Finding[]
            └── PRQueueAgent    → Finding[]
```

All three agents run concurrently by default. MCP servers can be written in any language — this codebase uses TypeScript/Bun for custom servers and the official GitHub MCP Go binary, demonstrating MCP's language-agnostic value.

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

### github-mcp-server

The official GitHub MCP server (`github-mcp-server stdio`) — a Go binary installed via Homebrew. Exposes GitHub's API as MCP tools.

Configured with `GITHUB_TOOLSETS=pull_requests,notifications` (restricts to only the tools we need) and `GITHUB_READ_ONLY=1`.

### Brewmaster agent

Calls homebrew-mcp tools concurrently, sends results to Claude for analysis, classifies version jumps (patch/minor/major), and produces structured `Finding` objects with severity labels.

### DevEnv agent

Calls all four devenv-mcp tools concurrently, sends results to Claude for analysis, classifies version jumps, and produces `Finding` objects. The local semver classifier is authoritative; Claude's value is the fallback for non-semver version strings.

### PR Queue agent

Calls `search_pull_requests` twice concurrently — once for PRs awaiting your review, once for your own open PRs. Deduplicates, enriches with relative timestamps ("3 days ago"), and sends combined data to Claude for triage. Maps Claude's severity classification directly to `Finding` objects. Produces a single all-clear info finding if no PRs need attention.

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
│   │   ├── devenv.py           # Dev tool versions agent
│   │   └── pr_queue.py         # GitHub PR triage agent
│   ├── contracts/
│   │   └── models.py           # Pydantic models (Finding, AgentResult, etc.)
│   ├── skills/
│   │   ├── mcp_utils.py        # call_tool, parse_tool_result, strip_fences
│   │   ├── semver.py           # Version jump classification
│   │   ├── severity.py         # Severity mapping
│   │   ├── time_context.py     # relative_time() utility
│   │   └── timing.py           # ms_timer, elapsed_ms
│   ├── cli.py                  # Typer CLI + Rich renderer
│   ├── config.py               # SERVER_REGISTRY, MODEL, VERSION
│   └── orchestrator.py         # ServerManager + Orchestrator
├── evals/
│   ├── test_brewmaster.py      # Brewmaster integration tests
│   ├── test_devenv.py          # DevEnv integration tests
│   ├── test_homebrew_mcp.py    # homebrew-mcp contract tests
│   ├── test_orchestrator.py    # Orchestrator integration tests
│   ├── test_pr_queue.py        # PR Queue integration tests
│   └── test_time_context.py    # time_context unit tests
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

# GitHub MCP server (Go binary)
brew install github-mcp-server
```

**Secrets:** Copy `op.env` entries to your 1Password vault, or export the variables directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_TOKEN=ghp_...
export GITHUB_USERNAME=your-github-username
```

## Running

```bash
# Needs ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_USERNAME — use 1Password or export directly
op run --env-file=op.env -- uv run morning-agents

# Options
morning-agents --help
morning-agents --quiet              # titles only, no detail lines
morning-agents --no-parallel        # run agents sequentially
morning-agents -a brewmaster        # run a specific agent (repeat for multiple)
morning-agents -a brewmaster -a devenv  # run two agents explicitly

# JSON output is always written to stdout. Capture or redirect as needed:
op run --env-file=op.env -- uv run morning-agents > briefing.json
```

## Tests

```bash
op run --env-file=op.env -- uv run pytest evals/ -v
```

31 tests total (as of session 5). Integration tests require `ANTHROPIC_API_KEY` and `GITHUB_TOKEN`. The `test_time_context.py` tests are pure unit tests and need no secrets.

---

## Where it's going

### ~~Session 4 - devenv-mcp + DevEnv agent~~ (complete)
Second MCP server checking Xcode, VS Code, Node, and Python versions against latest. Runs alongside Brewmaster concurrently.

### ~~Session 5 - GitHub MCP + PR Queue~~ (complete)
PR Queue agent using the official `github-mcp-server` Go binary. Searches for PRs awaiting review and open PRs authored by you. All three agents run concurrently by default.

### Session 6 - Cross-references + polish
Correlates findings across agents (e.g., a major Node upgrade flagged by both devenv and a GitHub PR). Adds run persistence to `runs/`.

### Session 7 - Evals + governance
Eval suite with an LLM judge, read-only scope enforcement, max tool call limits, and execution logging.

### Session 8 - Architecture diagrams + polish
Architecture diagrams, eval suite hardening, and final cleanup.
