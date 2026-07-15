"""Agent delegation manager (Module 4).

Decides *which* agent runs a task and *actually runs it*, with the resilience the
brief asks for:

* **Choose the best agent** — pluggable :class:`RoutingStrategy` (default:
  capability match, health- and load-aware).
* **Avoid duplicate work** — consults the safety guard's signature ledger and
  reuses the prior output for an identical unit of work.
* **Retry failed agents** — bounded retries per the schedule policy.
* **Handle unavailable agents** — falls back to the next candidate agent, then
  fails the task gracefully (never raises into the engine).

Routing is fully injectable, so "future dynamic routing" (load balancing,
cost-aware, model-tiered) is a new :class:`RoutingStrategy` — no engine change.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.models import AgentOutput, Task
from src.ai.orchestration.registry.agent_registry import (
    OrchestrationAgent,
    OrchestrationRegistry,
)
from src.ai.orchestration.safety.guards import OrchestrationSafetyGuard


class DelegationError(Exception):
    """Raised only when delegation cannot proceed at all (no candidates)."""


class RoutingStrategy(ABC):
    """Selects an ordered candidate list of agents for a task."""

    @abstractmethod
    def rank(
        self, task: Task, candidates: List[OrchestrationAgent]
    ) -> List[OrchestrationAgent]:
        """Return ``candidates`` ordered best-first for ``task``."""


class CapabilityRoutingStrategy(RoutingStrategy):
    """Default routing: prefer healthy agents, then those advertising fewer
    capabilities (more specialised), then fewest recent invocations (load), then
    name for determinism."""

    def __init__(self) -> None:
        self._load: Dict[str, int] = {}

    def rank(
        self, task: Task, candidates: List[OrchestrationAgent]
    ) -> List[OrchestrationAgent]:
        """Order candidates best-first (specialisation + health + load)."""
        from src.ai.orchestration.registry.agent_registry import HealthStatus

        def _key(agent: OrchestrationAgent):
            d = agent.descriptor
            health_rank = 0 if d.health == HealthStatus.HEALTHY else 1
            specialisation = len(d.capabilities)
            load = self._load.get(d.name, 0)
            return (health_rank, specialisation, load, d.name)

        return sorted(candidates, key=_key)

    def record_use(self, agent_name: str) -> None:
        """Increment the observed load for ``agent_name`` (for load balancing)."""
        self._load[agent_name] = self._load.get(agent_name, 0) + 1


class DelegationManager:
    """Chooses and invokes agents for tasks, resiliently."""

    def __init__(
        self,
        registry: OrchestrationRegistry,
        *,
        strategy: Optional[RoutingStrategy] = None,
        safety: Optional[OrchestrationSafetyGuard] = None,
    ) -> None:
        """Wire the manager to a registry, routing strategy and safety guard."""
        self.registry = registry
        self.strategy = strategy or CapabilityRoutingStrategy()
        self.safety = safety or OrchestrationSafetyGuard()

    # -- selection ----------------------------------------------------------

    def candidates_for(self, task: Task) -> List[OrchestrationAgent]:
        """Return the ranked, usable candidate agents for ``task``."""
        found = self.registry.discover(task.capability, healthy_only=True)
        usable = [
            a for a in found if a.can_handle(task) and self.safety.is_agent_usable(a)
        ]
        return self.strategy.rank(task, usable)

    def choose(self, task: Task) -> Optional[OrchestrationAgent]:
        """Return the single best agent for ``task`` (or ``None`` if none)."""
        candidates = self.candidates_for(task)
        return candidates[0] if candidates else None

    # -- execution ----------------------------------------------------------

    def delegate(
        self,
        task: Task,
        context: SharedContext,
        *,
        max_retries: int = 1,
        depth: int = 0,
    ) -> AgentOutput:
        """Run ``task`` on the best available agent, with retries + fallback.

        Never raises for expected failures — returns an :class:`AgentOutput` with
        ``ok=False`` so the engine can decide whether the workflow degrades or
        fails. Only a total absence of candidate agents yields an error output.
        """
        self.safety.before_execution(task, depth=depth)

        # De-duplication: identical work already ran → reuse its recorded output.
        is_new = self.safety.register_execution(task)
        if not is_new:
            prior = context.output_of(task.id) or {}
            return AgentOutput(
                task_id=task.id,
                agent="(deduplicated)",
                ok=True,
                data=prior,
                summary="Reused prior identical result (duplicate work avoided).",
            )

        candidates = self.candidates_for(task)
        if not candidates:
            return AgentOutput(
                task_id=task.id,
                agent="(none)",
                ok=False,
                error=(
                    f"No healthy agent advertises capability {task.capability!r}."
                ),
            )

        last_error: Optional[str] = None
        # Try each candidate; retry the *same* candidate up to max_retries first.
        for agent in candidates:
            for attempt in range(max_retries + 1):
                output = self._invoke(agent, task, context)
                if isinstance(self.strategy, CapabilityRoutingStrategy):
                    self.strategy.record_use(agent.descriptor.name)
                if output.ok:
                    return output
                last_error = output.error
            # this candidate exhausted its retries → fall back to the next agent

        return AgentOutput(
            task_id=task.id,
            agent=candidates[0].descriptor.name,
            ok=False,
            error=last_error or "All candidate agents failed.",
        )

    def _invoke(
        self, agent: OrchestrationAgent, task: Task, context: SharedContext
    ) -> AgentOutput:
        """Invoke one agent defensively, timing it and normalising exceptions."""
        start = time.perf_counter()
        try:
            output = agent.execute(task, context)
        except Exception as exc:  # an agent must never crash the engine
            output = AgentOutput(
                task_id=task.id,
                agent=agent.descriptor.name,
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        output.agent = agent.descriptor.name
        output.task_id = task.id
        if not output.latency_ms:
            output.latency_ms = (time.perf_counter() - start) * 1000.0
        return output
