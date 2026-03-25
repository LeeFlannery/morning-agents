from __future__ import annotations

import asyncio
import sys
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from morning_agents.config import SERVER_REGISTRY


class ServerManager:
    """
    Manages MCP server lifecycles. Starts only the servers that enabled
    agents actually need. Provides connected ClientSession objects keyed
    by server name.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._contexts: list[Any] = []

    @property
    def active_server_names(self) -> set[str]:
        return set(self._sessions.keys())

    def get_sessions(self, server_names: list[str]) -> dict[str, ClientSession]:
        return {name: self._sessions[name] for name in server_names if name in self._sessions}

    def get_all_sessions(self) -> dict[str, ClientSession]:
        return dict(self._sessions)

    async def start_servers(self, needed: set[str]) -> None:
        known = {name for name in needed if name in SERVER_REGISTRY}
        for name in needed - known:
            print(f"[ServerManager] WARNING: '{name}' not in registry, skipping", file=sys.stderr)

        async def _start_safe(name: str) -> None:
            try:
                await asyncio.wait_for(self._start_one(name), timeout=15.0)
            except Exception as e:
                print(f"[ServerManager] ERROR: failed to start '{name}': {e}", file=sys.stderr)

        await asyncio.gather(*[_start_safe(name) for name in known])

    async def _start_one(self, name: str) -> None:
        params = SERVER_REGISTRY[name]

        stdio_ctx = stdio_client(params)
        read, write = await stdio_ctx.__aenter__()
        self._contexts.append(stdio_ctx)

        session_ctx = ClientSession(read, write)
        session = await session_ctx.__aenter__()
        self._contexts.append(session_ctx)

        await session.initialize()
        self._sessions[name] = session

    async def shutdown(self) -> None:
        for ctx in reversed(self._contexts):
            try:
                await ctx.__aexit__(None, None, None)
            except Exception as e:
                print(f"[ServerManager] WARNING during shutdown: {e}", file=sys.stderr)
