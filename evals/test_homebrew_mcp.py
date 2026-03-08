"""
Integration tests for homebrew-mcp.
Connects via stdio, calls all 3 tools, validates response shapes.
"""
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/homebrew-mcp/index.ts"],
)


def parse(result) -> dict:
    return json.loads(result.content[0].text)


async def test_tools_available():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {
                "list_outdated",
                "get_package_info",
                "get_doctor_status",
            }


async def test_list_outdated_shape():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = parse(await session.call_tool("list_outdated", {}))
            assert "error" not in result
            assert "formulae" in result
            assert "casks" in result
            for f in result["formulae"]:
                assert {"name", "current", "latest", "pinned"} <= f.keys()
            for c in result["casks"]:
                assert {"name", "current", "latest"} <= c.keys()


async def test_get_package_info_shape():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = parse(await session.call_tool("get_package_info", {"name": "git"}))
            assert "error" not in result
            for field in ("name", "version", "desc", "homepage", "dependencies"):
                assert field in result
            assert result["name"] == "git"
            assert result["version"]


async def test_get_doctor_status_shape():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = parse(await session.call_tool("get_doctor_status", {}))
            assert "error" not in result
            assert isinstance(result["healthy"], bool)
            assert isinstance(result["warnings"], list)
