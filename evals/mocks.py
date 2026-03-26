from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from morning_agents.contracts.models import AgentResult


@dataclass
class MockToolContent:
    text: str


@dataclass
class MockToolResult:
    content: list[MockToolContent]
    isError: bool = False


@dataclass
class MockTool:
    name: str


@dataclass
class MockListToolsResult:
    tools: list[MockTool]


class MockMCPSession:
    """Returns frozen tool outputs for golden test cases.

    fixtures: { tool_name: raw_output_dict }
    Each call_tool invocation JSON-encodes the fixture and wraps it in MockToolResult.
    """

    def __init__(self, fixtures: dict[str, Any]) -> None:
        self.fixtures = fixtures
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, arguments: dict | None = None) -> MockToolResult:
        self.calls.append((tool_name, arguments or {}))
        if tool_name not in self.fixtures:
            return MockToolResult(
                content=[MockToolContent(text=json.dumps({"error": f"Unknown tool: {tool_name}"}))],
                isError=True,
            )
        return MockToolResult(
            content=[MockToolContent(text=json.dumps(self.fixtures[tool_name]))]
        )

    async def list_tools(self) -> MockListToolsResult:
        return MockListToolsResult(tools=[MockTool(name=name) for name in self.fixtures])


def load_upstream_fixture(filepath: str) -> dict[str, AgentResult]:
    """Load frozen upstream AgentResult objects from a JSON fixture file."""
    with open(filepath) as f:
        data = json.load(f)

    return {
        agent_name: AgentResult.model_validate(raw)
        for agent_name, raw in data["upstream"].items()
    }
