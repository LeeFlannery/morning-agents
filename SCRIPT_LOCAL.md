# Video Script Ideas — Morning Agents

This file tracks candidate video topics based on what was built each session. Update it each pre-push pipeline run.

---

## Session 7 — Golden Test Framework

### 1. "How to Test an AI Agent Without Mocking the AI"
**Description:** Walk through the golden test pattern: freeze real tool outputs as JSON fixtures, let the agent run against them deterministically, then use an LLM judge (Haiku) to evaluate the findings semantically. Show why this beats both unit testing (too brittle) and full integration testing (too slow and nondeterministic).
**Why now:** The full pattern is complete and working. It's a novel approach that most ML engineers haven't seen applied to agentic systems.

---

### 2. "Building a Regression Detector for AI Output"
**Description:** Show `evals/regression.py` -- how to compare two `BriefingOutput` snapshots and emit structured flags for finding count drops, severity spikes, and detail quality degradation. Demo `morning-agents diff` against a real baseline. Discuss the thresholds (50% count drop, 3x severity spike, 40% detail drop) and how to tune them.
**Why now:** This is a gap in almost every agentic project -- people don't track output quality over time. The diff command makes it concrete.

---

### 3. "LLM-as-Judge: Grading Your Agent With Haiku"
**Description:** Deep dive into `evals/judge.py`. Show the prompt structure: input data, agent findings, criterion with expected values and finding_match filter, chain-of-thought instruction, JSON-only output. Show how `asyncio.gather` fans out one Haiku call per criterion in parallel. Discuss why Haiku is the right model here (speed, cost, sufficient reasoning for binary pass/fail).
**Why now:** LLM-as-judge is becoming a standard pattern; showing a minimal, working implementation is more useful than another theoretical explanation.

---

### 4. "MockMCPSession: Testing MCP-Backed Agents Without Live Servers"
**Description:** Show how `MockMCPSession` replaces a live MCP server in tests by returning frozen JSON fixtures. Walk through the fixture format, the `fixtures: {tool_name -> output}` dict structure, and why the mock implements `list_tools` in addition to `call_tool`. Contrast with mocking at the HTTP layer.
**Why now:** This is the missing piece most people hit when they try to test MCP-backed code. The implementation is small enough to explain in under 5 minutes.

---

### 5. "DAG Orchestration for AI Agents — Dependency Graph Deep Dive"
**Description:** Walk through `dag_executor.py` and `test_dag_executor.py`. Show TopologicalSorter usage, tier execution, failure propagation (skip dependents on failure), soft deps (missing agents silently ignored), and semaphore limiting. Show the diamond dependency test to make the tier concept concrete.
**Why now:** The test file documents every interesting edge case. Recording it while the decisions are fresh means the test code itself becomes the script outline.

---

## Earlier Sessions (backlog)

### 6. "Building a Morning Briefing CLI with Claude and MCP"
**Description:** Overview of the full project: how agents declare `mcp_servers`, how the orchestrator wires them up over stdio, how findings flow into `BriefingOutput`, and how Rich renders it to stderr while JSON goes to stdout.
**Why now:** Good intro video. Film after the project is more stable.

### 7. "The Two-Tier Output Pattern: Rich to stderr, JSON to stdout"
**Description:** Explain why Rich output goes to stderr and JSON always goes to stdout. Show how this makes the CLI both human-readable and pipeable. Demo `morning-agents | jq '.summary'` and `morning-agents > briefing.json`.
**Why now:** Simple concept, surprisingly uncommon in CLI tools. Short video.
