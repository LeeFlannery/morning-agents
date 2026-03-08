from __future__ import annotations

import json


def strip_fences(text: str) -> str:
    """Strip markdown code fences from a string if present."""
    if not text.strip().startswith("```"):
        return text
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("```")
    )


def parse_tool_result(result) -> dict:
    """Parse a JSON MCP tool result, stripping markdown fences if present."""
    return json.loads(strip_fences(result.content[0].text))
