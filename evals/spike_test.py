"""
Spike test: Python MCP client <-> TypeScript MCP server over stdio.
Proves the bridge works before we build the real homebrew-mcp.
"""
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/spike/index.ts"],
)


async def test_tools_available():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {"hello", "add"}


async def test_hello_tool():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("hello", {"name": "Lee"})
            assert "The bridge works" in result.content[0].text


async def test_add_tool():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("add", {"a": 21, "b": 21})
            assert result.content[0].text == "42"
