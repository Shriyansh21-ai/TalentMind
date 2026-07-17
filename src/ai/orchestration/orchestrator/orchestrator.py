"""AgentOrchestrator — the top-level coordinator (Module 1).

The single public entry point of the framework. Given a high-level
:class:`Goal` it:

    1. Understands the objective (delegated to the planner).
    2. Breaks the work into tasks (the planner's :class:`TaskGraph`).
    3. Selects agents + executes the workflow (delegation + engine).
    4. Monitors execution (the monitor observes the event stream).
    5. Merges outputs into one unified response.

Critically — per the brief — the orchestrator **contains no hiring business
logic**. It knows about goals, tasks, agents and outputs; it knows nothing about
candidates, résumés or interviews. All domain knowledge lives in the agents that
future milestones register.

Everything is injected, so a future milestone swaps the planner (e.g. for an
LLM planner) or the engine's policies without touching this class.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.events.emitter import EventEmitter, TelemetryEventBridge
from src.ai.orchestration.models import AgentOutput, Goal, TaskGraph
from src.ai.orchestration.monitoring.monitor import WorkflowMonitor
from src.ai.orchestration.planner.planner import (
    CapabilityTaskPlanner,
    TaskPlanner,
    default_plan_templates,
)
from src.ai.orchestration.registry.agent_registry import (
    OrchestrationRegistry,
    orchestration_registry,
)
from src.ai.orchestration.state.state import WorkflowState, WorkflowStatus
from src.ai.orchestration.workflow.engine import (
    CancellationToken,
    WorkflowEngine,
    WorkflowResult,
)


@dataclass
class OrchestrationResult:
    """The unified response of orchestrating a goal.

    Attributes:
        goal: The originating goal.
        status: Overall :class:`WorkflowStatus`.
        answer: A merged, human-readable synthesis of the task outputs.
        outputs: ``{task_id: AgentOutput}`` for every task that ran.
        task_count: Number of tasks planned.
        evidence_sources: Distinct sources cited across outputs.
        warnings: Soft advisories from safety / execution.
        latency_ms: Total wall-clock time (planning + execution + merge).
        workflow_id: The underlying workflow run id.
        state: The final :class:`WorkflowState`.
        graph: The planned :class:`TaskGraph` (for introspection / visualization).
        error: Populated only on a hard failure.
    """

    goal: Goal
    status: WorkflowStatus
    answer: str = ""
    outputs: dict[str, AgentOutput] = field(default_factory=dict)
    task_count: int = 0
    evidence_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    workflow_id: str = ""
    state: WorkflowState | None = None
    graph: TaskGraph | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Return ``True`` when the run completed fully or partially."""
        return self.status in {WorkflowStatus.COMPLETED, WorkflowStatus.PARTIAL}

    def merged_data(self) -> dict[str, Any]:
        """Return ``{task_id: output.data}`` for successful tasks (unified view)."""
        return {tid: o.data for tid, o in self.outputs.items() if o.ok}


class AgentOrchestrator:
    """Coordinates planning → execution → monitoring → merge for a goal."""

    def __init__(
        self,
        *,
        registry: OrchestrationRegistry | None = None,
        planner: TaskPlanner | None = None,
        engine: WorkflowEngine | None = None,
        monitor: WorkflowMonitor | None = None,
        telemetry_bridge: bool = True,
    ) -> None:
        """Wire the orchestrator's collaborators (all optional; sane defaults)."""
        self.registry = registry or orchestration_registry
        self.planner = planner or CapabilityTaskPlanner(default_plan_templates())
        self.events = EventEmitter()
        self.engine = engine or WorkflowEngine(registry=self.registry, events=self.events)
        # Ensure the monitor + telemetry observe the engine's emitter.
        self.events = self.engine.events
        self.monitor = monitor or WorkflowMonitor()
        self.monitor.attach(self.events)
        self._telemetry_off = None
        if telemetry_bridge:
            self._telemetry_off = TelemetryEventBridge().attach(self.events)

    # -- public API ---------------------------------------------------------

    def run(
        self,
        goal: Goal,
        *,
        context: SharedContext | None = None,
        cancellation: CancellationToken | None = None,
    ) -> OrchestrationResult:
        """Orchestrate ``goal`` end-to-end and return a unified result."""
        start = time.perf_counter()

        # 1-2) Understand + decompose.
        graph = self.planner.plan(goal)

        # 3-4) Execute + monitor (the engine emits; the monitor observes).
        context = context or SharedContext()
        result = self.engine.run(
            graph,
            context=context,
            name=self._workflow_name(goal, graph),
            cancellation=cancellation,
        )

        # 5) Merge into a unified response.
        merged = self._merge(goal, result)
        merged.latency_ms = (time.perf_counter() - start) * 1000.0
        merged.task_count = len(graph)
        merged.graph = graph
        return merged

    def plan_only(self, goal: Goal) -> TaskGraph:
        """Return the planned task graph without executing it (introspection)."""
        return self.planner.plan(goal)

    # -- internals ----------------------------------------------------------

    def _workflow_name(self, goal: Goal, graph: TaskGraph) -> str:
        """Derive a workflow name from the plan template (falls back to goal)."""
        for task in graph:
            template = task.metadata.get("plan_template")
            if template and template != "(default)":
                return template
        return "goal_workflow"

    def _merge(self, goal: Goal, result: WorkflowResult) -> OrchestrationResult:
        """Merge task outputs into one unified, human-readable answer.

        Pure aggregation — no domain interpretation. Prefers an explicit
        ``synthesis`` output if one exists, otherwise concatenates each task's
        one-line summary in topological order.
        """
        outputs = result.outputs
        sources: list[str] = []
        for output in outputs.values():
            for src in output.evidence_sources:
                if src not in sources:
                    sources.append(src)

        # A synthesis/summary task, if present, is the headline answer.
        headline = ""
        for output in outputs.values():
            if output.ok and output.data.get("synthesis"):
                headline = str(output.data["synthesis"])
                break

        lines: list[str] = []
        for tid, output in outputs.items():
            marker = "•" if output.ok else "✗"
            summary = output.summary or (output.error or "(no summary)")
            lines.append(f"{marker} [{tid}] {summary}")

        if headline:
            answer = headline + "\n\n" + "\n".join(lines)
        elif lines:
            answer = (
                f"Completed {len(result.successful_outputs())}/{len(outputs)} "
                f"task(s) for the goal.\n\n" + "\n".join(lines)
            )
        else:
            answer = "No tasks produced output for this goal."

        return OrchestrationResult(
            goal=goal,
            status=result.status,
            answer=answer,
            outputs=outputs,
            evidence_sources=sources,
            warnings=result.warnings,
            workflow_id=result.workflow_id,
            state=result.state,
            error=result.error,
        )
