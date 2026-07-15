"""Shared orchestration vocabulary.

The small set of typed contracts every orchestration module speaks. Kept free of
any engine / provider / UI import so it can be shared by the planner, scheduler,
delegation manager, workflow engine and the agents without coupling.

Nothing here is hiring-specific: a :class:`Task` carries an abstract *capability*
string (the kind of agent it needs), never a concrete business behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional


class Priority(IntEnum):
    """Task priority (higher runs first within a schedulable group)."""

    LOW = 0
    NORMAL = 10
    HIGH = 20
    CRITICAL = 30


class TaskStatus(str, Enum):
    """Lifecycle status of a single task."""

    PENDING = "pending"      # created, dependencies not yet satisfied
    READY = "ready"          # dependencies satisfied, awaiting execution
    RUNNING = "running"      # currently executing on an agent
    COMPLETED = "completed"  # finished successfully
    FAILED = "failed"        # exhausted retries / hard error
    SKIPPED = "skipped"      # conditional guard or a failed dependency
    CANCELLED = "cancelled"  # workflow was cancelled before it ran

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` when no further transition is possible."""
        return self in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.SKIPPED,
            TaskStatus.CANCELLED,
        }


@dataclass
class Goal:
    """A high-level recruiter objective handed to the orchestrator.

    Attributes:
        description: Natural-language objective (e.g. "Assess CAND_1 for the JD").
        subject_id: Primary entity the goal concerns (candidate id, job id, …).
        constraints: Free-form constraints/hints the planner may honour.
        metadata: Arbitrary caller metadata (never interpreted by the framework).
    """

    description: str
    subject_id: str = "global"
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """A single unit of work in a :class:`TaskGraph`.

    A task is *composable*: it names the capability it needs (not a concrete
    agent), declares its dependencies by id, and carries an opaque ``payload``
    the chosen agent knows how to consume. The orchestrator/scheduler/delegation
    layers reason purely over these fields.

    Attributes:
        id: Unique task id within its graph.
        goal: Human-readable sub-goal this task achieves.
        capability: The agent *capability* required to run it (routing key).
        priority: Scheduling priority within a parallel group.
        dependencies: Ids of tasks that must complete before this one runs.
        expected_output: Human description of the artefact this task produces.
        confidence: Planner confidence (0-100) that this task is well-formed.
        payload: Opaque, agent-specific input (the framework never inspects it).
        optional: If ``True``, a failure does not fail the whole workflow.
        condition: Optional key looked up in shared context; task runs only if truthy.
        metadata: Arbitrary planner metadata.
    """

    id: str
    goal: str
    capability: str
    priority: Priority = Priority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    expected_output: str = ""
    confidence: float = 100.0
    payload: Dict[str, Any] = field(default_factory=dict)
    optional: bool = False
    condition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        """Return a stable identity used to detect duplicate work.

        Two tasks with the same capability + goal + payload are considered the
        same unit of work by the delegation de-duplication guard.
        """
        import json

        return f"{self.capability}|{self.goal}|" + json.dumps(
            self.payload, sort_keys=True, default=str
        )


@dataclass
class AgentOutput:
    """The standardized result an agent returns for one task.

    Deliberately mirrors the shape of the platform's :class:`AgentResult` /
    :class:`ToolResult` so downstream merging is uniform.

    Attributes:
        task_id: The task this output answers.
        agent: Name of the agent that produced it.
        ok: Whether the task succeeded.
        data: Structured, JSON-serializable result payload.
        summary: One-line human summary.
        confidence: 0-100 confidence in the output.
        evidence_sources: Engines / sources the agent used.
        latency_ms: Wall-clock execution time.
        error: Error message when ``ok`` is ``False``.
    """

    task_id: str
    agent: str
    ok: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    confidence: float = 100.0
    evidence_sources: List[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None


class GraphError(Exception):
    """Raised when a :class:`TaskGraph` is structurally invalid."""


@dataclass
class TaskGraph:
    """A directed acyclic graph of :class:`Task` objects.

    The planner produces one; the scheduler layers it; the workflow engine
    executes it. The graph validates itself (unknown dependencies + cycles) so
    no downstream module has to.
    """

    tasks: Dict[str, Task] = field(default_factory=dict)
    goal: Optional[Goal] = None

    def add(self, task: Task) -> Task:
        """Add ``task`` to the graph (last write wins on duplicate id)."""
        self.tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task:
        """Return the task with ``task_id`` (raises :class:`GraphError` if absent)."""
        if task_id not in self.tasks:
            raise GraphError(f"Unknown task id {task_id!r}.")
        return self.tasks[task_id]

    def __len__(self) -> int:
        """Return the number of tasks."""
        return len(self.tasks)

    def __iter__(self):
        """Iterate over tasks (insertion order)."""
        return iter(self.tasks.values())

    def validate(self) -> None:
        """Validate referential integrity and acyclicity.

        Raises:
            GraphError: On an unknown dependency or a dependency cycle.
        """
        for task in self.tasks.values():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    raise GraphError(
                        f"Task {task.id!r} depends on unknown task {dep!r}."
                    )
        self.topological_order()  # raises on a cycle

    def topological_order(self) -> List[Task]:
        """Return tasks in a dependency-respecting order.

        Uses Kahn's algorithm; ties are broken by descending priority then id so
        the ordering is deterministic (important for caching and tests).

        Raises:
            GraphError: If the graph contains a cycle.
        """
        indegree = {tid: 0 for tid in self.tasks}
        for task in self.tasks.values():
            for dep in task.dependencies:
                indegree[task.id] += 1

        ready = [tid for tid, deg in indegree.items() if deg == 0]
        order: List[Task] = []
        while ready:
            ready.sort(key=lambda tid: (-int(self.tasks[tid].priority), tid))
            current = ready.pop(0)
            order.append(self.tasks[current])
            for task in self.tasks.values():
                if current in task.dependencies:
                    indegree[task.id] -= 1
                    if indegree[task.id] == 0:
                        ready.append(task.id)

        if len(order) != len(self.tasks):
            raise GraphError("Task graph contains a dependency cycle.")
        return order

    def execution_layers(self) -> List[List[Task]]:
        """Group tasks into parallel-executable layers (topological levels).

        Every task in layer *n* depends only on tasks in layers ``< n``, so a
        whole layer can run in parallel. Within a layer, tasks are ordered by
        descending priority.
        """
        self.validate()
        depth: Dict[str, int] = {}

        def _depth(tid: str, seen: Optional[set] = None) -> int:
            seen = seen or set()
            if tid in seen:
                raise GraphError("Task graph contains a dependency cycle.")
            if tid in depth:
                return depth[tid]
            deps = self.tasks[tid].dependencies
            value = 0 if not deps else 1 + max(_depth(d, seen | {tid}) for d in deps)
            depth[tid] = value
            return value

        for tid in self.tasks:
            _depth(tid)

        layers: Dict[int, List[Task]] = {}
        for tid, level in depth.items():
            layers.setdefault(level, []).append(self.tasks[tid])

        ordered: List[List[Task]] = []
        for level in sorted(layers):
            group = sorted(
                layers[level], key=lambda t: (-int(t.priority), t.id)
            )
            ordered.append(group)
        return ordered
