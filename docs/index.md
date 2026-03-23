# morning-agents

A CLI tool that runs a structured morning briefing. Agents run in parallel, each backed by an MCP server, and produce `Finding` objects. Results are correlated across agents, persisted to `runs/`, and rendered to the terminal via Rich — with JSON always going to stdout for piping.

## Quick Start

```bash
uv tool install .
morning-agents
```

See the [Quickstart guide](quickstart.md) for full setup instructions.

## What It Does

Each run:

1. Starts the required MCP servers
2. Runs all agents in parallel
3. Correlates findings across agents (`cross_references`)
4. Persists the full `BriefingOutput` to `runs/`
5. Renders to stderr (Rich) and stdout (JSON)

## Agents

| Agent | MCP Server | Checks |
|---|---|---|
| `BrewmasterAgent` | `homebrew-mcp` | Outdated Homebrew packages + `brew doctor` warnings |
| `DevEnvAgent` | `devenv-mcp` | Xcode, VSCode, Node, Python version freshness |
| `PRQueueAgent` | `github-mcp` | PRs awaiting your review + your open PRs |

## Output

Progress and Rich rendering → **stderr**
JSON (`BriefingOutput`) → **stdout**

This means you can pipe or redirect stdout cleanly:

```bash
morning-agents | jq '.summary'
morning-agents > briefing.json
```
