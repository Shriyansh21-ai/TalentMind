"""Agent Registry v2 (Module 9).

Upgrades the platform's simple name->agent registry into a capability- and
health-aware discovery service that future agents plug into with zero changes to
the orchestrator:

* **Dynamic discovery** — find agents by *capability*, not by class.
* **Rich metadata** — version, dependencies, tool requirements, tags.
* **Health status** — the delegation layer avoids unhealthy agents.
* **Plugin-ready** — anything implementing :class:`OrchestrationAgent` registers
  itself; nothing else in the framework needs editing.

There is intentionally **no hiring logic** here: a capability is an opaque
string (e.g. ``"resume_analysis"``) that future milestones define.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock

from src.ai.orchestration.models import AgentOutput, Task


class HealthStatus(str, Enum):
    """Operational health of a registered agent."""

    HEALTHY = "healthy"  # ready to accept work
    DEGRADED = "degraded"  # usable but suspect (e.g. recent failures)
    UNHEALTHY = "unhealthy"  # must not be delegated to
    UNKNOWN = "unknown"  # not yet probed


@dataclass
class AgentDescriptor:
    """Static + dynamic metadata describing a registered agent.

    Attributes:
        name: Unique agent key.
        version: Agent version (part of routing/telemetry identity).
        capabilities: Capability strings this agent can satisfy (routing keys).
        description: One-line description.
        dependencies: Names of other agents/services this agent relies on.
        tool_requirements: Tool names the agent needs available to run.
        tags: Free-form discovery tags.
        health: Current :class:`HealthStatus` (mutated by monitoring/delegation).
        max_concurrency: Advisory hint for the scheduler (future async execution).
    """

    name: str
    version: str = "v1"
    capabilities: list[str] = field(default_factory=list)
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    tool_requirements: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    health: HealthStatus = HealthStatus.HEALTHY
    max_concurrency: int = 1

    def handles(self, capability: str) -> bool:
        """Return ``True`` iff this agent advertises ``capability``."""
        return capability in self.capabilities


class OrchestrationAgent(ABC):
    """The contract every orchestratable agent implements.

    This is intentionally tiny — the whole point of the milestone is that a
    future agent needs only to (1) declare a :class:`AgentDescriptor` and (2)
    implement :meth:`execute`. The agent owns all domain logic; the framework
    owns planning, scheduling, delegation, retries, safety and monitoring.

    Concrete agents typically *wrap* an existing engine, tool or
    :class:`~src.ai.core.base_agent.BaseAgent` — see
    :mod:`src.ai.orchestration.adapters` for ready-made adapters.
    """

    #: Static identity + capabilities of the agent.
    descriptor: AgentDescriptor

    def can_handle(self, task: Task) -> bool:
        """Return ``True`` iff this agent can execute ``task``.

        Default policy: capability match. Override for finer-grained routing
        (e.g. inspecting the payload). Never called for unhealthy agents.
        """
        return self.descriptor.handles(task.capability)

    @abstractmethod
    def execute(self, task: Task, context) -> AgentOutput:
        """Run ``task`` against the shared ``context`` and return an output.

        Implementations must never raise for expected failures — return an
        :class:`AgentOutput` with ``ok=False`` and an ``error`` instead. The
        delegation layer will still catch unexpected exceptions defensively.
        """


class OrchestrationRegistry:
    """Thread-safe, capability-indexed registry of orchestration agents."""

    def __init__(self) -> None:
        self._agents: dict[str, OrchestrationAgent] = {}
        self._lock = RLock()

    # -- registration -------------------------------------------------------

    def register(self, agent: OrchestrationAgent) -> OrchestrationAgent:
        """Register ``agent`` under its descriptor name (last write wins)."""
        with self._lock:
            self._agents[agent.descriptor.name] = agent
        return agent

    def unregister(self, name: str) -> None:
        """Remove an agent by name (no-op if absent)."""
        with self._lock:
            self._agents.pop(name, None)

    # -- lookup -------------------------------------------------------------

    def get(self, name: str) -> OrchestrationAgent:
        """Return the agent registered under ``name`` (raises ``KeyError``)."""
        with self._lock:
            if name not in self._agents:
                raise KeyError(f"No orchestration agent registered under {name!r}.")
            return self._agents[name]

    def has(self, name: str) -> bool:
        """Return ``True`` iff ``name`` is registered."""
        with self._lock:
            return name in self._agents

    def names(self) -> list[str]:
        """Return all registered agent names (sorted)."""
        with self._lock:
            return sorted(self._agents)

    def all(self) -> list[OrchestrationAgent]:
        """Return every registered agent."""
        with self._lock:
            return list(self._agents.values())

    # -- dynamic discovery --------------------------------------------------

    def discover(self, capability: str, *, healthy_only: bool = True) -> list[OrchestrationAgent]:
        """Return agents advertising ``capability``.

        Args:
            capability: The routing key to match.
            healthy_only: Exclude agents whose health is ``UNHEALTHY``.
        """
        with self._lock:
            agents = list(self._agents.values())
        matches = [a for a in agents if a.descriptor.handles(capability)]
        if healthy_only:
            matches = [a for a in matches if a.descriptor.health != HealthStatus.UNHEALTHY]
        return matches

    def capabilities(self) -> dict[str, list[str]]:
        """Return ``{capability: [agent_name, ...]}`` across all agents."""
        index: dict[str, list[str]] = {}
        for agent in self.all():
            for cap in agent.descriptor.capabilities:
                index.setdefault(cap, []).append(agent.descriptor.name)
        return {cap: sorted(names) for cap, names in index.items()}

    def describe(self) -> list[dict[str, object]]:
        """Return a JSON-serializable descriptor list (for the UI / telemetry)."""
        rows: list[dict[str, object]] = []
        for agent in self.all():
            d = agent.descriptor
            rows.append(
                {
                    "name": d.name,
                    "version": d.version,
                    "capabilities": list(d.capabilities),
                    "health": d.health.value,
                    "tool_requirements": list(d.tool_requirements),
                    "dependencies": list(d.dependencies),
                    "tags": list(d.tags),
                }
            )
        return sorted(rows, key=lambda r: r["name"])

    def set_health(self, name: str, health: HealthStatus) -> None:
        """Update an agent's health status (used by monitoring/delegation)."""
        with self._lock:
            if name in self._agents:
                self._agents[name].descriptor.health = health


# Process-wide default registry. Future agents call
# ``orchestration_registry.register(...)`` at import time.
orchestration_registry = OrchestrationRegistry()
