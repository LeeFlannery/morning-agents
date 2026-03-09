# CLAUDE.md

Project-level instructions for Claude Code. Loaded automatically every session.

---

## Tooling

- **Package manager:** `uv` — always use `uv run`, `uv add`, `uv sync`. Never pip or poetry.
- **MCP server runtime:** `bun` — never node or npx.
- **Run tests:** `op run --env-file=op.env -- uv run pytest evals/`
- **Run the CLI:** `op run --env-file=op.env -- uv run morning-agents`
- **Secrets:** API keys live in `op.env` as `op://` references. Never put real keys in any file.

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
- `morning_agents/config.py` — SERVER_REGISTRY, MODEL, VERSION constants
- `mcp-servers/` — TypeScript/Bun only, one folder per server
- `evals/` — integration tests, not unit tests

---

## Known constraints

- **anyio cancel scopes** cannot be exited in a different task than they were entered. The MCP SDK uses anyio task groups internally. `ServerManager` uses manual `__aenter__`/`__aexit__` with exception swallowing in `shutdown()` — this is intentional, not a bug. Do not replace with `AsyncExitStack`.

---

## Claude model

Use `claude-sonnet-4-6` for all agent reasoning calls. Defined as `MODEL` in `config.py`.

---

## Behavior

- Run `/simplify` before every commit.
- Keep solutions minimal — don't add features or refactor beyond what's asked.
- Don't create new files unless necessary.
