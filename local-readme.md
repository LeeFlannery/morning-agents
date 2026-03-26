# Local README — Architect Handoff

**Last updated:** 2026-03-25 (session 7 — pre-push pipeline complete)

---

## What was done this session (session 7)

### Golden test framework
Four new golden tests (`test_golden_brewmaster.py`, `test_golden_devenv.py`, `test_golden_pr_queue.py`, `test_golden_cross_ref.py`) that freeze real tool outputs as JSON fixtures and use an LLM judge (claude-haiku-4-5-20251001) to grade each agent's findings against semantic criteria defined in YAML.

### LLM judge (`evals/judge.py`)
`judge_agent_output()` fans out one Haiku API call per criterion check using `asyncio.gather`. Returns a `JudgeVerdict` with per-check `CheckResult` objects. Parse failures default to `passed=False` rather than raising.

### Mock MCP session (`evals/mocks.py`)
`MockMCPSession` replaces live MCP servers in golden tests. It takes a `fixtures` dict (`tool_name -> raw_output`) and returns frozen JSON responses. `load_upstream_fixture()` deserializes frozen `AgentResult` objects for cross-ref golden tests.

### Regression detector (`evals/regression.py`)
`detect_regressions(baseline, current)` compares two `BriefingOutput` objects and emits `RegressionFlag` structs for: agent failures, finding count drops >50%, severity spikes >3x, detail quality drops >40%, and DAG stage changes.

### New CLI commands added to `cli.py`
- `morning-agents eval` -- runs all golden suites in parallel (depth-0 concurrent, cross-ref after)
- `morning-agents diff <run-id>` -- regression report comparing a saved baseline to the most recent run

### DAG executor tests (`evals/test_dag_executor.py`)
Seven unit tests covering: single-tier, linear chain, diamond dependency, cycle detection, failure propagation, soft deps (missing dep silently ignored), and semaphore limiting.

### Regression unit tests (`evals/test_regression.py`)
Seven unit tests covering all four regression flag types plus the no-regression baseline case.

### `ResourceContext` extracted to `morning_agents/orchestrator/resources.py`
The `ResourceContext` dataclass now lives in its own module to avoid circular imports when golden tests import it alongside agent classes.

### Version bump
`config.py` version updated to `0.1.002`.

---

## Current architecture

```
morning_agents/
  cli.py                  -- typer app; subcommands: (default), history, last, show, eval, diff
  config.py               -- MODEL, VERSION, SERVER_REGISTRY, MAX_CONCURRENT_API_CALLS
  contracts/models.py     -- all Pydantic models (source of truth)
  agents/
    base.py               -- BaseAgent ABC; __init_subclass__ enforces name/display_name/mcp_servers
    brewmaster.py         -- Homebrew outdated + doctor
    devenv.py             -- Xcode, VSCode, Node, Python version checks
    pr_queue.py           -- GitHub PRs awaiting review + your open PRs
    cross_ref.py          -- pure correlation; no MCP, no Claude; depends_on all depth-0 agents
  orchestrator/
    __init__.py           -- re-exports Orchestrator
    orchestrator.py       -- main Orchestrator class
    dag_executor.py       -- execute_dag(); uses graphlib.TopologicalSorter
    server_manager.py     -- ServerManager; manual __aenter__/__aexit__ (intentional, see CLAUDE.md)
    resources.py          -- ResourceContext dataclass
  persistence.py          -- save/load BriefingOutput to runs/ as JSON
  skills/
    cross_reference.py    -- find_cross_references()
    mcp_utils.py          -- call_tool(), parse_tool_result(), strip_fences()
    semver.py             -- classify() for version jump classification
    severity.py           -- from_version_jump()
    time_context.py       -- relative_time()
    timing.py             -- elapsed_ms(), ms_timer()

evals/
  judge.py               -- LLM judge using Haiku
  mocks.py               -- MockMCPSession, load_upstream_fixture()
  regression.py          -- detect_regressions()
  golden/                -- frozen fixtures + criteria YAML per agent
    brewmaster/           -- outdated_packages.json, doctor_warnings.json, criteria.yaml
    devenv/               -- tool_versions.json, criteria.yaml
    pr_queue/             -- search_results.json, criteria.yaml
    cross_ref/            -- upstream_results.json, criteria.yaml
  test_golden_*.py        -- golden test per agent
  test_regression.py      -- unit tests for regression detector
  test_dag_executor.py    -- unit tests for DAG executor
  test_*.py               -- existing integration tests
```

---

## Intentionally deferred / incomplete

1. **Fixture refresh workflow** -- no tooling yet to update frozen fixtures when real tool outputs change. Current approach: manual. Should be a `morning-agents capture` command or a script.
2. **`JUDGE_MODEL` not in config.py** -- `evals/judge.py` hardcodes `"claude-haiku-4-5-20251001"`. Should move to `config.py` alongside `MODEL` for consistency.
3. **Golden test boilerplate** -- all four `test_golden_*.py` files share an identical structure (load fixture, build mock session, run agent, judge, assert score >= 0.8). Could be extracted to a shared `run_golden_suite()` helper in `evals/`. Deferred to keep each test file self-contained for now.
4. **`pyyaml` declared but only used in tests/cli eval** -- was added in anticipation of YAML config. Now legitimately used in `eval` command and golden tests.
5. **`compute_summary()` called twice per agent** -- once in `agent.run()` (for some agents) and once explicitly in golden tests. Known harmless duplicate; not worth refactoring now.
6. **`morning_agents/orchestrator/` vs `morning_agents/orchestrator.py`** -- `orchestrator.py` now lives inside the `orchestrator/` package as `orchestrator/orchestrator.py`. The top-level `morning_agents/orchestrator.py` was deleted this session. Imports should all go through `morning_agents.orchestrator` (the package `__init__` re-exports `Orchestrator`).

---

## Open questions / decisions for the architect

1. **Fixture refresh strategy** -- should `morning-agents capture` write golden fixtures from a live run? If so, does it overwrite or append? What's the branching story (fixtures should be committed but tied to a specific environment).
2. **Judge model** -- Haiku 4.5 is fast and cheap. Should there be a `--judge-model` flag on `morning-agents eval` for when you want higher confidence?
3. **Score threshold** -- all golden tests assert `score >= 0.8`. Should this be configurable per-agent in the criteria YAML?
4. **Run persistence format** -- currently `runs/<briefing_id>.json`. Should runs also be indexed (e.g., a `runs/index.json`) so `morning-agents history` doesn't need to glob?

---

## Known tech debt

- `asyncio` import inside `_run_eval`'s local block for `asyncio.Semaphore` is now gone (cleaned up this session) -- `asyncio` is module-level in cli.py.
- `yaml`, `json`, `Path` are still imported inside `_run_eval` body -- intentional lazy load pattern.
- `cross_ref.py` no longer hand-rolls `FindingSummary`; both code paths now call `compute_summary()`. The double-call (once in agent, once in orchestrator) is still present -- known harmless duplicate.
- Unused `f`-string prefix on `console.print` in `diff_runs` was removed in pre-push pipeline.

---

## Suggested next steps

1. Add `morning-agents capture` command to refresh golden fixtures from a live run.
2. Move `JUDGE_MODEL` to `config.py`.
3. Session 8 focus (per architect plan): run persistence cross-references, or notification integration.
4. Consider a `--threshold` flag on criteria YAML or `morning-agents eval` for per-agent score floors.

---

## Traps and gotchas

- **Golden test relative paths** -- `Path("evals/golden/...")` in test fixtures assumes pytest is run from the project root. If run from a subdirectory, fixtures won't be found. The fix is `Path(__file__).parent / "golden" / ...` -- deferred.
- **`MockMCPSession` fixture key is tool name, not server name** -- the fixture dict maps `tool_name -> output`, not `server_name -> output`. When constructing mocks, the key must match the exact tool name the agent calls (e.g., `"list_outdated"` not `"homebrew-mcp"`).
- **CrossRef upstream fixture format** -- `upstream_results.json` wraps everything under `{"upstream": {"agent_name": AgentResult_dict}}`. `load_upstream_fixture()` expects this shape exactly.
- **`morning-agents diff` exits 1 on critical flags** -- this is intentional for CI usage. Don't pipe it into a script that treats any non-zero exit as failure unless you handle it.
- **`ServerManager` uses manual async context management** -- documented in CLAUDE.md. Do not replace with AsyncExitStack.
