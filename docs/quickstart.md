# Quickstart

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/)
- Homebrew

---

## 1. Clone and install dependencies

```bash
git clone https://github.com/LeeFlannery/morning-agents.git
cd morning-agents

# Python deps
uv sync

# TypeScript MCP servers
cd mcp-servers && bun install && cd ..

# GitHub MCP server (Go binary)
brew install github-mcp-server
```

---

## 2. Set your secrets

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GITHUB_TOKEN=ghp_...
export GITHUB_USERNAME=your-github-username
```

Or use 1Password with the included `op.env` file:

```bash
op run --env-file=op.env -- morning-agents
```

---

## 3. Install the CLI globally

```bash
uv tool install .
```

This adds `morning-agents` to your PATH. You only need to do this once. To update after pulling changes:

```bash
uv tool install . --reinstall
```

---

## 4. Run it

```bash
morning-agents
```

Progress renders to your terminal. JSON output goes to stdout. Pipe or redirect as needed:

```bash
morning-agents | jq '.summary'
morning-agents > briefing.json
```

---

## Common options

```bash
morning-agents --quiet              # titles only, no detail lines
morning-agents --agent brewmaster   # run one agent
morning-agents --json               # JSON output only, no Rich rendering
morning-agents --no-persist         # skip saving to runs/
```

---

## View past runs

```bash
morning-agents history              # list recent runs
morning-agents last                 # re-render the most recent run
morning-agents show brief-2026-03-23-091500
```
