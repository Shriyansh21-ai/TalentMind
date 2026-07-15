"""Orchestration safety guards (Module 13).

Structural protections the whole framework relies on to *fail safe*:

* **Infinite loops** — a hard cap on total task executions per workflow.
* **Circular delegation** — cycle detection in the task graph + a per-task
  delegation-depth cap.
* **Repeated / duplicate execution** — a signature ledger so the same unit of
  work is never run twice in a run.
* **Conflicting outputs** — detection when two tasks claim the same output slot.
* **Unhealthy agents** — a gate the delegation layer consults.

The guard *raises* only for hard structural violations (loops/cycles). Softer
conditions (duplicates, conflicts) are reported so the caller can degrade
gracefully rather than crash — "Graceful degradation."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, List, Set

from src.ai.orchestration.models import Task, TaskGraph
from src.ai.orchestration.registry.agent_registry import (
    HealthStatus,
    OrchestrationAgent,
)


class OrchestrationSafetyError(Exception):
    """Raised on a hard structural safety violation (loop / cycle / overrun)."""


@dataclass
class SafetyLimits:
    """Configurable safety ceilings.

    Attributes:
        max_total_executions: Hard cap on task executions per workflow (anti-loop).
        max_delegation_depth: Max chained delegations for a single task.
        max_graph_size: Reject absurdly large graphs early.
    """

    max_total_executions: int = 200
    max_delegation_depth: int = 10
    max_graph_size: int = 500


class OrchestrationSafetyGuard:
    """Enforces structural safety across a workflow run (thread-safe)."""

    def __init__(self, limits: SafetyLimits | None = None) -> None:
        """Bind the guard to a set of :class:`SafetyLimits`."""
        self.limits = limits or SafetyLimits()
        self._executions = 0
        self._signatures: Set[str] = set()
        self._output_owner: Dict[str, str] = {}
        self._warnings: List[str] = []
        self._lock = RLock()

    # -- graph-level checks -------------------------------------------------

    def validate_graph(self, graph: TaskGraph) -> None:
        """Validate a graph before execution (raises on hard violations)."""
        if len(graph) > self.limits.max_graph_size:
            raise OrchestrationSafetyError(
                f"Task graph too large ({len(graph)} > {self.limits.max_graph_size})."
            )
        try:
            graph.validate()  # unknown deps + cycle detection
        except Exception as exc:  # normalise to a safety error (circular delegation)
            raise OrchestrationSafetyError(str(exc)) from exc
        self._check_output_conflicts(graph)

    def _check_output_conflicts(self, graph: TaskGraph) -> None:
        """Warn when two tasks declare the same output slot (conflicting outputs)."""
        owners: Dict[str, str] = {}
        for task in graph:
            slot = task.metadata.get("output_slot")
            if not slot:
                continue
            if slot in owners:
                self._warn(
                    f"Tasks {owners[slot]!r} and {task.id!r} both write output slot "
                    f"{slot!r}; later write wins."
                )
            else:
                owners[slot] = task.id

    # -- execution-time checks ---------------------------------------------

    def before_execution(self, task: Task, depth: int = 0) -> None:
        """Gate a task execution (raises on overrun / delegation depth)."""
        with self._lock:
            self._executions += 1
            if self._executions > self.limits.max_total_executions:
                raise OrchestrationSafetyError(
                    "Execution ceiling exceeded — aborting to prevent an infinite loop."
                )
        if depth > self.limits.max_delegation_depth:
            raise OrchestrationSafetyError(
                f"Delegation depth {depth} exceeds cap for task {task.id!r} "
                "(possible circular delegation)."
            )

    def register_execution(self, task: Task) -> bool:
        """Record a task's signature; return ``True`` if it is *new* work.

        A ``False`` return means an identical unit of work already ran — the
        caller should reuse the prior result instead of executing again.
        """
        sig = task.signature()
        with self._lock:
            if sig in self._signatures:
                self._warn(f"Duplicate task {task.id!r} skipped (already executed).")
                return False
            self._signatures.add(sig)
            return True

    def claim_output(self, task_id: str, slot: str) -> None:
        """Claim an output ``slot`` for ``task_id`` (warns on conflict)."""
        with self._lock:
            if slot in self._output_owner and self._output_owner[slot] != task_id:
                self._warn(
                    f"Output slot {slot!r} reassigned from "
                    f"{self._output_owner[slot]!r} to {task_id!r}."
                )
            self._output_owner[slot] = task_id

    def is_agent_usable(self, agent: OrchestrationAgent) -> bool:
        """Return ``True`` iff ``agent`` is healthy enough to receive work."""
        return agent.descriptor.health != HealthStatus.UNHEALTHY

    # -- reporting ----------------------------------------------------------

    def _warn(self, message: str) -> None:
        """Record a soft warning (deduplicated)."""
        if message not in self._warnings:
            self._warnings.append(message)

    @property
    def warnings(self) -> List[str]:
        """Return the accumulated soft warnings."""
        with self._lock:
            return list(self._warnings)

    @property
    def executions(self) -> int:
        """Return the number of gated executions so far."""
        return self._executions
