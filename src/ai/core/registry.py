"""Agent registry.

A tiny service locator so agents can be discovered by name (for the UI, for a
future multi-agent router, and for tests) without callers importing concrete
agent classes. Agents register themselves at import time.
"""

from __future__ import annotations

from typing import Dict, List

from src.ai.core.base_agent import BaseAgent
from src.ai.core.exceptions import AgentNotFoundError


class AgentRegistry:
    """In-process registry mapping agent name -> agent instance."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> BaseAgent:
        """Register ``agent`` under its metadata name; returns the agent.

        Registering the same name again replaces the previous instance (last
        definition wins), which keeps hot-reload / re-import behaviour sane.
        """
        self._agents[agent.metadata.name] = agent
        return agent

    def get(self, name: str) -> BaseAgent:
        """Return the agent registered under ``name``.

        Raises:
            AgentNotFoundError: If no such agent is registered.
        """
        agent = self._agents.get(name)
        if agent is None:
            raise AgentNotFoundError(f"No agent registered under {name!r}.")
        return agent

    def has(self, name: str) -> bool:
        """Return ``True`` iff ``name`` is registered."""
        return name in self._agents

    def names(self) -> List[str]:
        """Return all registered agent names (sorted)."""
        return sorted(self._agents.keys())

    def all(self) -> List[BaseAgent]:
        """Return all registered agents."""
        return list(self._agents.values())


# Process-wide default registry. Agents call ``registry.register(...)`` at import.
registry = AgentRegistry()
