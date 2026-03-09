from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import ClientSession

MCP_TOOL_TIMEOUT = 30.0  # seconds


def strip_fences(text: str) -> str:
    """Strip markdown code fences from a string if present."""
    if not text.strip().startswith("```"):
        return text
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("```")
    )


def parse_tool_result(result: Any) -> dict:
    """Parse a JSON MCP tool result, stripping markdown fences if present."""
    return json.loads(strip_fences(result.content[0].text))


async def call_tool(
    session: ClientSession,
    tool_name: str,
    arguments: dict,
    timeout: float = MCP_TOOL_TIMEOUT,
) -> Any:
    """Call an MCP tool with timeout and 1 retry on transient failure."""
    last_exc: BaseException | None = None
    for attempt in range(2):
        try:
            return await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            last_exc = TimeoutError(
                f"Tool '{tool_name}' timed out after {timeout}s "
                f"(attempt {attempt + 1}/2)"
            )
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(1.0)
                last_exc = e
            else:
                raise
    raise last_exc  # type: ignore[misc]
