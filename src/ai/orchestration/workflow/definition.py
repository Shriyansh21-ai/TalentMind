"""Declarative workflow definitions (Module 3).

The brief's key requirement: *"Future workflows should require configuration
instead of code changes."* A :class:`WorkflowDefinition` is that configuration —
a list of :class:`WorkflowStep` records (capability + dependencies + policy) that
the engine compiles into a :class:`~src.ai.orchestration.models.TaskGraph` and
executes. Defining a new workflow is data, not code.

The same definition can be authored inline, loaded from a dict (e.g. JSON/YAML
in a future milestone), or produced by the planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.ai.orchestration.models import Priority, Task, TaskGraph


class ExecutionMode(str, Enum):
    """How the engine should traverse a workflow's steps.

    ``AUTO`` (default) derives parallelism from the dependency graph — the most
    general mode. ``SEQUENTIAL`` and ``PARALLEL`` are explicit overrides useful
    for simple/flat workflows and for tests.
    """

    AUTO = "auto"  # parallelism inferred from dependencies
    SEQUENTIAL = "sequential"  # one task at a time, declaration order
    PARALLEL = "parallel"  # every (dependency-free) task at once


@dataclass
class RetryPolicy:
    """Per-workflow retry + fallback policy.

    Attributes:
        max_retries: Attempts beyond the first for a failing task.
        fallback_capability: Capability to try if the primary capability fails
            (config-driven fallback — no code change to add a fallback path).
        continue_on_failure: If ``True``, a failed *required* task degrades the
            run to ``PARTIAL`` rather than aborting it.
    """

    max_retries: int = 1
    fallback_capability: str | None = None
    continue_on_failure: bool = True


@dataclass
class WorkflowStep:
    """One declarative step in a :class:`WorkflowDefinition`.

    Attributes:
        id: Step id (becomes the task id).
        capability: Capability required to run the step.
        goal: Human-readable sub-goal.
        depends_on: Ids of steps that must complete first.
        priority: Scheduling priority.
        optional: If ``True``, failure never fails the workflow.
        condition: Context key that must be truthy for the step to run
            (conditional execution) — otherwise the step is skipped.
        expected_output: Description of the artefact produced.
        payload: Static payload merged into the task (agent-specific input).
        output_slot: Named context slot this step's output claims (conflict check).
    """

    id: str
    capability: str
    goal: str = ""
    depends_on: list[str] = field(default_factory=list)
    priority: Priority = Priority.NORMAL
    optional: bool = False
    condition: str | None = None
    expected_output: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    output_slot: str | None = None

    def to_task(self, base_payload: dict[str, Any] | None = None) -> Task:
        """Compile this step into a :class:`Task`, merging in ``base_payload``."""
        payload = dict(base_payload or {})
        payload.update(self.payload)
        metadata: dict[str, Any] = {}
        if self.output_slot:
            metadata["output_slot"] = self.output_slot
        return Task(
            id=self.id,
            goal=self.goal or self.capability,
            capability=self.capability,
            priority=self.priority,
            dependencies=list(self.depends_on),
            expected_output=self.expected_output,
            payload=payload,
            optional=self.optional,
            condition=self.condition,
            metadata=metadata,
        )


@dataclass
class WorkflowDefinition:
    """A reusable, named workflow expressed purely as configuration.

    Attributes:
        name: Unique workflow name.
        description: One-line description.
        steps: Ordered :class:`WorkflowStep` list.
        mode: :class:`ExecutionMode` traversal strategy.
        retry: :class:`RetryPolicy` for the run.
        version: Definition version (surfaced in telemetry / snapshots).
    """

    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    mode: ExecutionMode = ExecutionMode.AUTO
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    version: str = "v1"

    def build_graph(self, base_payload: dict[str, Any] | None = None) -> TaskGraph:
        """Compile the definition into a validated :class:`TaskGraph`.

        In ``SEQUENTIAL`` mode, an implicit chain dependency is added between
        consecutive steps so the graph enforces one-at-a-time ordering.
        """
        graph = TaskGraph()
        previous_id: str | None = None
        for step in self.steps:
            task = step.to_task(base_payload)
            if self.mode == ExecutionMode.SEQUENTIAL and previous_id:
                if previous_id not in task.dependencies:
                    task.dependencies.append(previous_id)
            if self.mode == ExecutionMode.PARALLEL:
                task.dependencies = []  # flatten: everything is independent
            graph.add(task)
            previous_id = step.id
        graph.validate()
        return graph

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowDefinition:
        """Build a definition from a plain dict (future JSON/YAML loading)."""
        steps = [
            WorkflowStep(
                id=s["id"],
                capability=s["capability"],
                goal=s.get("goal", ""),
                depends_on=list(s.get("depends_on", [])),
                priority=Priority[s["priority"]] if "priority" in s else Priority.NORMAL,
                optional=bool(s.get("optional", False)),
                condition=s.get("condition"),
                expected_output=s.get("expected_output", ""),
                payload=dict(s.get("payload", {})),
                output_slot=s.get("output_slot"),
            )
            for s in data.get("steps", [])
        ]
        retry_data = data.get("retry", {})
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            mode=ExecutionMode(data.get("mode", "auto")),
            retry=RetryPolicy(
                max_retries=int(retry_data.get("max_retries", 1)),
                fallback_capability=retry_data.get("fallback_capability"),
                continue_on_failure=bool(retry_data.get("continue_on_failure", True)),
            ),
            version=data.get("version", "v1"),
        )
