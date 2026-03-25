from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from morning_agents.agents.base import BaseAgent
from morning_agents.config import MAX_CONCURRENT_API_CALLS, VERSION
from morning_agents.contracts.models import (
    AgentStatus,
    BriefingConfig,
    BriefingOutput,
    BriefingSummary,
    CrossReference,
    ExecutionMeta,
)
from morning_agents.orchestrator.dag_executor import DAGExecutionError, execute_dag
from morning_agents.orchestrator.resources import ResourceContext
from morning_agents.orchestrator.server_manager import ServerManager
from morning_agents.persistence import persist_briefing
from morning_agents.skills.timing import elapsed_ms


class Orchestrator:
    """
    Runs a morning briefing. Manages the full lifecycle:
    resource setup -> server startup -> DAG execution -> result assembly -> cleanup.
    """

    def __init__(
        self,
        agent_classes: list[type[BaseAgent]],
        quiet_mode: bool = False,
        parallel: bool = True,
        persist: bool = True,
    ) -> None:
        self.agent_classes = agent_classes
        self.quiet_mode = quiet_mode
        self.parallel = parallel
        self.persist = persist

    async def run(self) -> BriefingOutput:
        start_time = datetime.now(timezone.utc)
        briefing_id = BriefingOutput.generate_id(start_time)

        max_concurrent = 1 if not self.parallel else MAX_CONCURRENT_API_CALLS
        semaphore = asyncio.Semaphore(max_concurrent)
        server_manager = ServerManager()

        resources = ResourceContext(
            semaphore=semaphore,
            workspace_root=Path("runs"),
            briefing_id=briefing_id,
            server_manager=server_manager,
        )

        agents: dict[str, BaseAgent] = {
            cls.name: cls(resources=resources) for cls in self.agent_classes
        }

        needed = {s for agent in agents.values() for s in agent.mcp_servers}
        await server_manager.start_servers(needed)

        try:
            dag_result = await execute_dag(agents, server_manager.get_all_sessions(), semaphore)
        except DAGExecutionError:
            raise
        finally:
            await server_manager.shutdown()

        now = datetime.now(timezone.utc)
        all_results = list(dag_result.results.values())

        # Extract CrossReference objects from the cross_ref agent's findings (if present)
        cross_refs: list[CrossReference] = []
        cross_ref_result = dag_result.results.get("cross_ref")
        if cross_ref_result:
            for f in cross_ref_result.findings:
                if f.category == "cross_reference":
                    cross_refs.append(CrossReference(
                        id=f.id,
                        severity=f.severity,
                        title=f.title,
                        detail=f.detail,
                        source_findings=f.metadata.get("source_findings", []),
                        source_agents=f.metadata.get("source_agents", []),
                        timestamp=f.timestamp,
                    ))

        all_findings = [f for r in all_results for f in r.findings]

        by_severity: dict[str, int] = {}
        for f in all_findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1

        servers_used = {
            s for agent in agents.values()
            for s in agent.mcp_servers
            if s in server_manager.active_server_names
        }

        output = BriefingOutput(
            version=VERSION,
            briefing_id=briefing_id,
            generated_at=now,
            duration_ms=elapsed_ms(start_time, now),
            agent_results=all_results,
            cross_references=cross_refs,
            summary=BriefingSummary(
                agents_run=len(all_results),
                agents_succeeded=sum(1 for r in all_results if r.status == AgentStatus.success),
                agents_failed=sum(1 for r in all_results if r.status == AgentStatus.error),
                total_findings=len(all_findings),
                by_severity=by_severity,
                mcp_servers_used=len(servers_used),
            ),
            execution=ExecutionMeta(
                stages=dag_result.tiers,
                dependency_graph={name: list(a.depends_on) for name, a in agents.items()},
                retries={},
            ),
            config=BriefingConfig(
                agents_enabled=[name for name in dag_result.results],
                quiet_mode=self.quiet_mode,
            ),
        )

        if self.persist:
            persist_briefing(output)

        return output
