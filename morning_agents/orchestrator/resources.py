from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from morning_agents.orchestrator.server_manager import ServerManager


@dataclass(frozen=True)
class ResourceContext:
    semaphore: asyncio.Semaphore
    workspace_root: Path
    briefing_id: str
    server_manager: "ServerManager | None" = None

    def get_workspace(self, agent_name: str) -> Path:
        """Create and return an isolated workspace directory for an agent run."""
        ws = self.workspace_root / self.briefing_id / agent_name
        ws.mkdir(parents=True, exist_ok=True)
        return ws
