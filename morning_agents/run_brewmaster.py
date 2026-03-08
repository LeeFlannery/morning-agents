"""
Quick runner: Brewmaster agent -> AgentResult JSON.
Usage: op run --env-file=op.env -- uv run python -m morning_agents.run_brewmaster
"""
import asyncio

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from morning_agents.agents.brewmaster import BrewmasterAgent
from morning_agents.config import HOMEBREW_MCP


async def main() -> None:
    agent = BrewmasterAgent()
    async with stdio_client(HOMEBREW_MCP) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await agent.run({"homebrew-mcp": session})

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
