# Morning Agents

A CLI morning briefing tool powered by Claude and MCP. Every morning, a set of agents runs in parallel, each backed by an MCP server, and drops a structured terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and anything else you wire up.

Inspired by Julia Cameron's ["Morning Pages"](https://www.amazon.com/Artists-Way-25th-Anniversary/dp/0143129252) from *The Artist's Way*. Same idea, different medium.

Python is the brains. TypeScript/Bun is the hands. Third-party Go binaries are welcome too.

**[Documentation](https://leeflannery.github.io/morning-agents/)**

---

## Architecture

A Python orchestrator spawns MCP servers as child processes over stdio. Each agent declares which servers it needs, the orchestrator starts them concurrently, and hands off connected sessions.

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

All three agents run concurrently by default. MCP servers can be written in any language. This repo uses TypeScript/Bun for custom servers and the official GitHub MCP Go binary.

## Agents

| Agent | MCP Server | What it checks |
|---|---|---|
| Brewmaster | `homebrew-mcp` (Bun/TS) | Outdated packages + `brew doctor` warnings |
| DevEnv | `devenv-mcp` (Bun/TS) | Xcode, VSCode, Node, Python version freshness |
| PR Queue | `github-mcp-server` (Go) | PRs awaiting your review + your open PRs |

## Output

Rich rendering goes to stderr. JSON (`BriefingOutput`) goes to stdout, pipeable and scriptable.

```bash
morning-agents | jq '.summary'
morning-agents > briefing.json
```

Every run is persisted to `runs/` and viewable with `morning-agents history`.

---

## Setup

**Requirements:** Python 3.13+, uv, Bun, Homebrew

```bash
git clone https://github.com/LeeFlannery/morning-agents.git
cd morning-agents

uv sync
cd mcp-servers && bun install && cd ..
brew install github-mcp-server

uv tool install .
```

**Secrets:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_TOKEN=ghp_...
export GITHUB_USERNAME=your-github-username
```

Then run:

```bash
morning-agents
```

Full setup in the [Quickstart](https://leeflannery.github.io/morning-agents/quickstart/).

---

## Tests

```bash
uv run pytest evals/ -v
```

Unit tests (no secrets): `test_persistence.py`, `test_cross_reference.py`, `test_time_context.py`

Integration tests (need `ANTHROPIC_API_KEY` and `GITHUB_TOKEN`): `test_brewmaster.py`, `test_devenv.py`, `test_pr_queue.py`
