from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from mcp import ClientSession

from morning_agents.config import MODEL
from morning_agents.contracts.models import AgentResult

if TYPE_CHECKING:
    from morning_agents.orchestrator.resources import ResourceContext


class BaseAgent(ABC):
    name: str
    display_name: str
    mcp_servers: list[str]
    depends_on: list[str] = []
    workspace_type: Literal["none", "scratch", "persistent"] = "none"
    model: str = MODEL

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("name", "display_name", "mcp_servers"):
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define class attribute '{attr}'")

    def __init__(self, resources: "ResourceContext | None" = None) -> None:
        self._resources = resources

    @abstractmethod
    async def run(
        self,
        sessions: dict[str, ClientSession],
        upstream: dict[str, AgentResult] | None = None,
    ) -> AgentResult:
        """Execute the agent. Receives connected MCP sessions and optional upstream results."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent's Claude API call."""
        ...

    @property
    def workspace(self) -> Path | None:
        """Returns the agent's isolated workspace directory, or None if not configured."""
        if self.workspace_type == "none" or self._resources is None:
            return None
        return self._resources.get_workspace(self.name)
