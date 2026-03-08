# CLAUDE.md

Project-level instructions for Claude Code. Loaded automatically every session.

---

## Tooling

- **Package manager:** `uv` — always use `uv run`, `uv add`, `uv sync`. Never pip or poetry.
- **MCP server runtime:** `bun` — never node or npx.
- **Run tests:** `uv run pytest evals/`
- **Run a specific eval:** `uv run python evals/<file>.py`

---

## Git

- **Never add co-author lines** to commit messages.
- Always ask before pushing.
- Always ask before force-pushing anything.
- Conventional commits style: `feat:`, `fix:`, `refactor:`, `perf:`, `docs:`, `chore:`

---

## Architecture

- `morning_agents/contracts/models.py` — source of truth for all data shapes. Change models here first.
- `morning_agents/agents/` — one file per agent, all inherit `BaseAgent`
- `morning_agents/skills/` — pure functions, no agent logic
- `mcp-servers/` — TypeScript/Bun only, one folder per server
- `evals/` — integration tests, not unit tests

---

## Claude Model

Use `claude-sonnet-4-6` for all agent reasoning calls.

---

## Behavior

- After completing code changes, run `/simplify` to review for quality and simplification.
- Keep solutions minimal — don't add features or refactor beyond what's asked.
- Don't create new files unless necessary.
