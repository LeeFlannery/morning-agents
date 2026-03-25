# Agents

## BrewmasterAgent

**File:** `morning_agents/agents/brewmaster.py`
**MCP Server:** `homebrew-mcp` (local Bun TypeScript server)
**Display name:** `🍺 Brewmaster`

Checks Homebrew package health. Calls two MCP tools concurrently:

- `list_outdated`: returns packages with current/latest versions
- `get_doctor_status`: returns warning strings

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
**Display name:** `🔀 PR Queue`

Surfaces GitHub PRs that need attention. Calls `search_pull_requests` twice concurrently:

- query `is:pr is:open review-requested:<user>` (PRs awaiting your review)
- query `is:pr is:open author:<user>` (your authored open PRs)

Enriches PR timestamps with relative time strings (`"3 days ago"`) via `time_context.relative_time()`. Passes enriched data to Claude for priority assessment.

**Finding metadata keys:**

| Key | Description |
|---|---|
| `tool_id` | `"github_pr"` |
| `pr_id` | PR number |
| `repo` | `owner/repo` |
| `url` | GitHub URL |
| `source` | `"github"` |

---

## CrossRefAgent

**File:** `morning_agents/agents/cross_ref.py`
**MCP Server:** none
**Display name:** `🔗 Cross-Reference`
**Depth:** 1 — `depends_on = ["brewmaster", "devenv", "pr_queue"]`

Runs after the three depth-0 agents complete. Receives their results as `upstream` and applies correlation rules from `skills/cross_reference.py` to find relationships across agents (e.g. a Node.js upgrade finding coinciding with Node-related open PRs).

Produces `Finding` objects with `category = "cross_reference"`. Does not call the Claude API or any MCP tools — pure Python logic over upstream findings.

**Finding metadata keys:**

| Key | Description |
|---|---|
| `source_findings` | List of finding IDs that triggered this cross-reference |
| `source_agents` | List of agent names involved |
