from __future__ import annotations

from abc import ABC, abstractmethod

from mcp import ClientSession

from morning_agents.contracts.models import AgentResult


class BaseAgent(ABC):
    name: str
    display_name: str
    mcp_servers: list[str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        for attr in ("name", "display_name", "mcp_servers"):
            if not hasattr(cls, attr):
                raise TypeError(f"{cls.__name__} must define class attribute '{attr}'")

    @abstractmethod
    async def run(self, sessions: dict[str, ClientSession]) -> AgentResult:
        """Execute the agent. Receives connected MCP sessions keyed by server name."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent's Claude API call."""
        ...
