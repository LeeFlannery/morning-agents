"""
Spike test: Python MCP client ↔ TypeScript MCP server over stdio.
Proves the bridge works before we build the real homebrew-mcp.
"""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_CMD = "bun"
SERVER_ARGS = ["run", "mcp-servers/spike/index.ts"]


async def run_spike():
    server_params = StdioServerParameters(
        command=SERVER_CMD,
        args=SERVER_ARGS,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"✅ Connected. Tools available: {[t.name for t in tools.tools]}")

            # Call hello tool
            result = await session.call_tool("hello", {"name": "Lee"})
            print(f"✅ hello tool: {result.content[0].text}")

            # Call add tool
            result = await session.call_tool("add", {"a": 21, "b": 21})
            print(f"✅ add tool: 21 + 21 = {result.content[0].text}")

    print("\n🎉 Spike passed. TS↔Python stdio MCP bridge confirmed.")


if __name__ == "__main__":
    asyncio.run(run_spike())
