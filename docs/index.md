# morning-agents

A CLI tool that runs a structured morning briefing. Agents run in parallel, each backed by an MCP server, and produce `Finding` objects. Results are correlated across agents, persisted to `runs/`, and rendered to the terminal via Rich — with JSON always going to stdout for piping.

## Quick Start

```bash
# Run the full briefing
morning-agents

# Suppress detail lines
morning-agents --quiet

# Run specific agents only
morning-agents --agent brewmaster --agent devenv

# Output JSON only (no Rich rendering)
morning-agents --json

# View run history
morning-agents history

# Re-render the most recent run
morning-agents last

# Show a specific run
morning-agents show brief-2026-03-23-091500
```

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
