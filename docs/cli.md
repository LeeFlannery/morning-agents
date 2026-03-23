# CLI Reference

## Installation

```bash
uv tool install .
```

Installs `morning-agents` globally into uv's tool environment and adds it to your PATH. Run once from the project directory — after that it works anywhere, no venv activation needed.

To update after pulling new changes:

```bash
uv tool install . --reinstall
```

---

Entry point: `morning-agents`

---

## `morning-agents` (default)

Run the full morning briefing.

```bash
morning-agents [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--agent`, `-a` | `brewmaster devenv pr_queue` | Agents to run. Repeat for multiple. |
| `--parallel / --no-parallel` | `--parallel` | Run agents in parallel. |
| `--quiet`, `-q` | off | Suppress detail lines in output. |
| `--json` | off | Output JSON only; skip Rich rendering. |
| `--no-persist` | off | Skip saving the run to `runs/`. |

**Examples:**

```bash
# Full briefing
morning-agents

# Quiet mode (just titles, no detail lines)
morning-agents --quiet

# Run one agent only
morning-agents --agent brewmaster

# JSON output for scripting
morning-agents --json | jq '.summary'

# Don't save this run
morning-agents --no-persist
```

---

## `morning-agents history`

List recent briefing runs.

```bash
morning-agents history [--limit N]
```

| Option | Default | Description |
|---|---|---|
| `--limit` | `10` | Number of runs to show. |

---

## `morning-agents last`

Re-render the most recent saved run.

```bash
morning-agents last
```

---

## `morning-agents show <run-id>`

Show a specific run by briefing ID.

```bash
morning-agents show brief-2026-03-23-091500
```

Run IDs are shown in `morning-agents history` output and are also the filenames in `runs/` (without the `.json` extension).

---

## Output

- **stderr** — Rich-rendered briefing (human-readable)
- **stdout** — `BriefingOutput` JSON (pipeable)

Exit code `1` if any agent errored.

---

## Runs Directory

Saved runs live in `runs/` relative to the working directory:

```
runs/
  brief-2026-03-23-091500.json
  brief-2026-03-22-083012.json
  ...
```

Each file is a full `BriefingOutput` JSON object.
