from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from morning_agents.agents.base import BaseAgent
from morning_agents.config import SERVER_REGISTRY, VERSION
from morning_agents.contracts.models import (
    AgentResult,
    AgentStatus,
    BriefingConfig,
    BriefingOutput,
    BriefingSummary,
    FindingSummary,
)
from morning_agents.skills.timing import elapsed_ms


class ServerManager:
    """
    Manages MCP server lifecycles. Starts only the servers that enabled
    agents actually need. Provides connected ClientSession objects keyed
    by server name.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._contexts: list[Any] = []  # anyio cancel scopes must be exited in their own task

    @property
    def active_server_names(self) -> set[str]:
        return set(self._sessions.keys())

    def get_sessions(self, server_names: list[str]) -> dict[str, ClientSession]:
        return {name: self._sessions[name] for name in server_names if name in self._sessions}

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


class Orchestrator:
    """
    Runs a morning briefing. Manages the full lifecycle:
    server startup -> agent execution -> result assembly -> cleanup.
    """

    def __init__(
        self,
        agents: list[BaseAgent],
        quiet_mode: bool = False,
        parallel: bool = True,
    ) -> None:
        self.agents = agents
        self.quiet_mode = quiet_mode
        self.parallel = parallel

    async def run(self) -> BriefingOutput:
        start_time = datetime.now(timezone.utc)

        needed = {s for agent in self.agents for s in agent.mcp_servers}
        server_manager = ServerManager()
        await server_manager.start_servers(needed)

        try:
            if self.parallel:
                results = list(await asyncio.gather(
                    *[self._run_agent_safe(agent, server_manager) for agent in self.agents]
                ))
            else:
                results = []
                for agent in self.agents:
                    results.append(await self._run_agent_safe(agent, server_manager))
        finally:
            await server_manager.shutdown()

        now = datetime.now(timezone.utc)

        servers_used = {
            s for agent in self.agents
            for s in agent.mcp_servers
            if s in server_manager.active_server_names
        }

        succeeded = [r for r in results if r.status == AgentStatus.success]
        failed = [r for r in results if r.status == AgentStatus.error]
        all_findings = [f for r in results for f in r.findings]

        by_severity: dict[str, int] = {}
        for f in all_findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

        return BriefingOutput(
            version=VERSION,
            briefing_id=BriefingOutput.generate_id(now),
            generated_at=now,
            duration_ms=elapsed_ms(start_time, now),
            agent_results=results,
            cross_references=[],
            summary=BriefingSummary(
                agents_run=len(results),
                agents_succeeded=len(succeeded),
                agents_failed=len(failed),
                total_findings=len(all_findings),
                by_severity=by_severity,
                mcp_servers_used=len(servers_used),
            ),
            config=BriefingConfig(
                agents_enabled=[a.name for a in self.agents],
                quiet_mode=self.quiet_mode,
            ),
        )

    async def _run_agent_safe(
        self, agent: BaseAgent, server_manager: ServerManager
    ) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        try:
            sessions = server_manager.get_sessions(agent.mcp_servers)
            missing = set(agent.mcp_servers) - set(sessions.keys())
            if missing:
                return self._error_result(
                    agent, started_at,
                    f"MCP servers unavailable: {', '.join(sorted(missing))}",
                )
            result = await asyncio.wait_for(agent.run(sessions), timeout=120.0)
            result.compute_summary()
            return result
        except asyncio.TimeoutError:
            return self._error_result(agent, started_at, "Agent timed out after 120s")
        except Exception as e:
            return self._error_result(
                agent, started_at, f"Unhandled error: {type(e).__name__}: {e}"
            )

    def _error_result(
        self, agent: BaseAgent, started_at: datetime, error_msg: str
    ) -> AgentResult:
        now = datetime.now(timezone.utc)
        return AgentResult(
            agent_name=agent.name,
            agent_display_name=agent.display_name,
            status=AgentStatus.error,
            started_at=started_at,
            completed_at=now,
            duration_ms=elapsed_ms(started_at, now),
            findings=[],
            summary=FindingSummary(total=0, by_severity={}),
            tool_calls=[],
            error=error_msg,
        )
