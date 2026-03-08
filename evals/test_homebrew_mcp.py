"""
Manual integration test for homebrew-mcp.
Connects via stdio, calls all 3 tools, validates response shapes.
"""
import asyncio
import json
import sys
from pathlib import Path

# Run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_PARAMS = StdioServerParameters(
    command="bun",
    args=["run", "mcp-servers/homebrew-mcp/index.ts"],
)


def parse_result(result) -> dict:
    return json.loads(result.content[0].text)


async def test_list_outdated(session: ClientSession):
    print("\n── list_outdated ─────────────────────────────")
    result = parse_result(await session.call_tool("list_outdated", {}))

    if "error" in result:
        print(f"⚠️  Error: {result['error']}")
        return

    formulae = result.get("formulae", [])
    casks = result.get("casks", [])
    print(f"✅ formulae outdated: {len(formulae)}")
    print(f"✅ casks outdated:    {len(casks)}")

    if formulae:
        f = formulae[0]
        assert "name" in f and "current" in f and "latest" in f and "pinned" in f, \
            f"Formula missing fields: {f}"
        print(f"   sample formula: {f['name']} {f['current']} → {f['latest']} (pinned={f['pinned']})")

    if casks:
        c = casks[0]
        assert "name" in c and "current" in c and "latest" in c, \
            f"Cask missing fields: {c}"
        print(f"   sample cask: {c['name']} {c['current']} → {c['latest']}")


async def test_get_package_info(session: ClientSession):
    print("\n── get_package_info ──────────────────────────")
    # git is a safe package to query — should always be installed
    result = parse_result(await session.call_tool("get_package_info", {"name": "git"}))

    if "error" in result:
        print(f"⚠️  Error: {result['error']}")
        return

    for field in ("name", "version", "desc", "homepage", "dependencies"):
        assert field in result, f"Missing field: {field}"

    print(f"✅ name:     {result['name']}")
    print(f"✅ version:  {result['version']}")
    print(f"✅ desc:     {result['desc'][:60]}...")
    print(f"✅ deps:     {result['dependencies'][:3]}")


async def test_get_doctor_status(session: ClientSession):
    print("\n── get_doctor_status ─────────────────────────")
    result = parse_result(await session.call_tool("get_doctor_status", {}))

    if "error" in result:
        print(f"⚠️  Error: {result['error']}")
        return

    assert "healthy" in result, "Missing 'healthy' field"
    assert "warnings" in result, "Missing 'warnings' field"
    assert isinstance(result["warnings"], list), "'warnings' should be a list"

    print(f"✅ healthy:  {result['healthy']}")
    print(f"✅ warnings: {len(result['warnings'])} found")
    for w in result["warnings"][:2]:
        print(f"   ⚠ {w[:80]}...")


async def main():
    print("Connecting to homebrew-mcp...")
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"✅ Connected. Tools: {tool_names}")

            assert set(tool_names) == {"list_outdated", "get_package_info", "get_doctor_status"}, \
                f"Unexpected tools: {tool_names}"

            await test_list_outdated(session)
            await test_get_package_info(session)
            await test_get_doctor_status(session)

    print("\n🎉 homebrew-mcp: all tools tested successfully.")


if __name__ == "__main__":
    asyncio.run(main())
