# Morning Agents

A CLI morning briefing tool powered by Claude and MCP. Every morning, a set of agents runs in parallel, each backed by an MCP server, and drops a structured terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and anything else you wire up.

Inspired by Julia Cameron's ["Morning Pages"](https://amzn.to/4d9HFNd) from *The Artist's Way*.

Python is the brains. TypeScript/Bun is the hands. Third-party Go binaries are welcome too. This is a work in progress. More agents are coming, and because the agent layer is built on MCP, you can add your own in any language.

**[Documentation](https://leeflannery.github.io/morning-agents/)**

---

## Architecture

A Python orchestrator spawns MCP servers as child processes over stdio. Agents declare dependencies on each other via `depends_on`. The orchestrator resolves the graph with `graphlib.TopologicalSorter` and runs each depth tier concurrently.

```
morning-agents (Python CLI)
    └── Orchestrator
            ├── ServerManager  ←→  stdio  ←→  homebrew-mcp (Bun/TS)
            │                  ←→  stdio  ←→  devenv-mcp (Bun/TS)
            │                  ←→  stdio  ←→  github-mcp-server (Go binary)
            │
            │  depth 0 (no deps, run concurrently)
            ├── BrewmasterAgent  → Finding[]
            ├── DevEnvAgent      → Finding[]
            ├── PRQueueAgent     → Finding[]
            │
            │  depth 1 (waits for depth 0, receives upstream results)
            └── CrossRefAgent    → Finding[]
```

MCP servers can be written in any language. Agents declare `depends_on = [...]` to receive upstream results. The `ResourceContext` provides each agent with a semaphore, isolated workspace, and server access.

## Agents

| Agent | MCP Server | What it checks | Depth |
|---|---|---|---|
| Brewmaster | `homebrew-mcp` (Bun/TS) | Outdated packages + `brew doctor` warnings | 0 |
| DevEnv | `devenv-mcp` (Bun/TS) | Xcode, VSCode, Node, Python version freshness | 0 |
| PR Queue | `github-mcp-server` (Go) | PRs awaiting your review + your open PRs | 0 |
| Cross-Reference | none | Correlates findings across depth-0 agents | 1 |

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

---

## License

Morning Agents is licensed under the Apache License 2.0.
Branding, site content, and related media assets are not included unless explicitly stated.
