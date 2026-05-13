# Morning Agents

**[MKDocs Complete documentation here!](https://leeflannery.github.io/morning-agents/)**

A CLI morning briefing tool powered by Claude and MCP. Every morning, a set of agents runs in parallel, each backed by an MCP server, and drops a structured terminal briefing: Homebrew health, dev tool versions, GitHub PRs, and anything else you wire up.

Inspired by Julia Cameron's ["Morning Pages"](https://amzn.to/4d9HFNd) from *The Artist's Way*.

Python is the brains. TypeScript/Bun is the hands. Third-party Go binaries are welcome too. This is a work in progress. More agents are coming, and because the agent layer is built on MCP, you can add your own in any language.

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

## Dashboard

A local web dashboard lets you browse and compare past briefing runs in your browser.

```bash
cd dashboard
bun install
bun dev
```

Open `http://localhost:5173`. The dashboard reads from the `runs/` directory via a Vite dev-server plugin -- no separate backend needed.

Features: run history list, per-run detail with agent cards and DAG visualization, and side-by-side diff between any two runs.

---

## Output

Rich rendering goes to stderr. JSON (`BriefingOutput`) goes to stdout, pipeable and scriptable.

```bash
morning-agents | jq '.summary'
morning-agents > briefing.json
```

Every run is persisted to `runs/` and viewable with the built-in subcommands:

```bash
morning-agents history       # list recent runs
morning-agents last          # replay most recent run
morning-agents show <run-id> # show a specific run
morning-agents eval          # run golden test suite against frozen fixtures
morning-agents diff <run-id> # regression report vs. most recent run
```

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
cp .env.example .env
# fill in ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_USERNAME
```

Or use 1Password with the included `op.env`:

```bash
op run --env-file=op.env -- morning-agents
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

**Unit tests (no secrets):** `test_persistence.py`, `test_cross_reference.py`, `test_time_context.py`, `test_dag_executor.py`, `test_regression.py`

**Integration tests** (need `ANTHROPIC_API_KEY` + `GITHUB_TOKEN`): `test_brewmaster.py`, `test_devenv.py`, `test_pr_queue.py`

**Golden tests** (need `ANTHROPIC_API_KEY`): freeze real tool outputs as fixtures and use an LLM judge (Haiku) to grade each agent's findings against semantic criteria. Run the full suite from the CLI:

```bash
morning-agents eval
```

## Regression Detection

Compare two saved runs to detect output degradation:

```bash
morning-agents diff <baseline-run-id>
morning-agents diff <baseline-run-id> --run-b <current-run-id>
```

Flags agent failures, finding count drops, detail quality drops, and DAG stage changes. Exits non-zero if any critical regression is found.

---

## License

Morning Agents is licensed under the Apache License 2.0.
Branding, site content, and related media assets are not included unless explicitly stated.
