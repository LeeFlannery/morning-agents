# Agents

## BrewmasterAgent

**File:** `morning_agents/agents/brewmaster.py`
**MCP Server:** `homebrew-mcp` (local Bun TypeScript server)
**Display name:** `🍺 Brewmaster`

Checks Homebrew package health. Calls two MCP tools concurrently:

- `list_outdated_packages` — returns packages with current/latest versions
- `run_brew_doctor` — returns warning strings

Passes results to Claude for severity assessment. Classifies version jumps (patch/minor/major) via `semver.classify()`.

**Finding metadata keys:**

| Key | Description |
|---|---|
| `tool_id` | Package name (lowercase) or `"brew_doctor"` |
| `package` | Package name |
| `current_version` | Installed version |
| `latest_version` | Latest available |
| `version_jump` | `patch` / `minor` / `major` / `unknown` |
| `source` | `"homebrew"` or `"brew_doctor"` |

---

## DevEnvAgent

**File:** `morning_agents/agents/devenv.py`
**MCP Server:** `devenv-mcp` (local Bun TypeScript server)
**Display name:** `🛠️  DevEnv`

Checks dev tool version freshness. Calls four MCP tools concurrently:

- `check_xcode_version`
- `check_vscode_version`
- `check_node_version`
- `check_python_version`

Feeds results to Claude with `tool_id` hints per tool. Uses `semver.classify()` as authoritative override over Claude's jump classification.

**Finding metadata keys:**

| Key | Description |
|---|---|
| `tool_id` | `xcode` / `vscode` / `node` / `python` |
| `tool` | Human display name |
| `installed_version` | Installed version |
| `latest_version` | Latest available |
| `version_jump` | `patch` / `minor` / `major` / `current` / `unknown` / `not_installed` |
| `source` | `"devenv"` |

---

## PRQueueAgent

**File:** `morning_agents/agents/pr_queue.py`
**MCP Server:** `github-mcp` (`github-mcp-server` binary)
**Display name:** `🔍 PR Queue`

Surfaces GitHub PRs that need attention. Calls:

- `list_pull_requests` (PRs awaiting your review)
- `list_pull_requests` (your authored open PRs)

Enriches PR timestamps with relative time strings (`"3 days ago"`) via `time_context.relative_time()`. Passes enriched data to Claude for priority assessment.

**Finding metadata keys:**

| Key | Description |
|---|---|
| `tool_id` | `"github_pr"` |
| `pr_id` | PR number |
| `repo` | `owner/repo` |
| `url` | GitHub URL |
| `category` | `"needs_review"` / `"my_open_pr"` |
| `age_relative` | Relative age string |
