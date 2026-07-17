"""Task scheduler (Module 8).

Turns a validated :class:`TaskGraph` into an *execution plan*: an ordered list of
parallel groups where every task in a group is independent of the others and
depends only on already-scheduled tasks. Within a group, tasks are ordered by
descending priority.

The scheduler owns *ordering + grouping + timeout/retry policy* — it does not run
anything. That separation lets the same plan drive synchronous execution today
and asynchronous / distributed execution in a future milestone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.ai.orchestration.models import Priority, Task, TaskGraph


@dataclass
class SchedulePolicy:
    """Execution policy applied to scheduled tasks.

    Attributes:
        default_timeout_s: Per-task timeout (seconds) when a task does not override.
        max_retries: Default retry attempts for a failed task.
        max_parallel: Cap on tasks executed concurrently within a group (future
            async execution honours this; the synchronous engine uses it as a hint).
    """

    default_timeout_s: float = 30.0
    max_retries: int = 1
    max_parallel: int = 8


@dataclass
class SchedulePlan:
    """A concrete plan derived from a task graph.

    Attributes:
        groups: Ordered parallel groups; ``groups[n]`` runs after ``groups[n-1]``.
        policy: The :class:`SchedulePolicy` in force.
    """

    groups: list[list[Task]] = field(default_factory=list)
    policy: SchedulePolicy = field(default_factory=SchedulePolicy)

    @property
    def total_tasks(self) -> int:
        """Return the total number of scheduled tasks."""
        return sum(len(group) for group in self.groups)

    @property
    def max_width(self) -> int:
        """Return the widest parallel group (peak concurrency)."""
        return max((len(group) for group in self.groups), default=0)

    def describe(self) -> list[dict]:
        """Return a JSON-serializable description of each group (for the UI)."""
        return [
            {
                "group": i,
                "tasks": [
                    {
                        "id": t.id,
                        "capability": t.capability,
                        "priority": Priority(t.priority).name,
                        "depends_on": list(t.dependencies),
                    }
                    for t in group
                ],
            }
            for i, group in enumerate(self.groups)
        ]


class TaskScheduler:
    """Builds a :class:`SchedulePlan` from a :class:`TaskGraph`."""

    def __init__(self, policy: SchedulePolicy | None = None) -> None:
        """Bind the scheduler to a :class:`SchedulePolicy` (default if omitted)."""
        self.policy = policy or SchedulePolicy()

    def schedule(self, graph: TaskGraph) -> SchedulePlan:
        """Return an execution plan of priority-ordered parallel groups.

        Raises:
            GraphError: If the graph is invalid (unknown dep or cycle).
        """
        groups = graph.execution_layers()  # validates + layers the graph
        # Respect the concurrency cap by splitting over-wide groups so the plan
        # already reflects the max_parallel policy (future async executors bind to it).
        capped: list[list[Task]] = []
        cap = max(1, self.policy.max_parallel)
        for group in groups:
            if len(group) <= cap:
                capped.append(group)
            else:
                for start in range(0, len(group), cap):
                    capped.append(group[start : start + cap])
        return SchedulePlan(groups=capped, policy=self.policy)

    def timeout_for(self, task: Task) -> float:
        """Return the effective timeout (seconds) for ``task``."""
        override = task.metadata.get("timeout_s")
        try:
            return float(override) if override is not None else self.policy.default_timeout_s
        except (TypeError, ValueError):
            return self.policy.default_timeout_s

    def retries_for(self, task: Task) -> int:
        """Return the effective retry count for ``task``."""
        override = task.metadata.get("max_retries")
        try:
            return int(override) if override is not None else self.policy.max_retries
        except (TypeError, ValueError):
            return self.policy.max_retries
