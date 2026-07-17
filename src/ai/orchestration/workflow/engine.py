"""Workflow execution engine (Module 3).

Executes a :class:`WorkflowDefinition` (or a raw :class:`TaskGraph`) by driving
the collaborating layers — scheduler, delegation, safety, events, state, memory —
without ever knowing what any task *does*. Everything the brief lists is here and
config-driven:

* **Sequential / parallel / conditional** execution (from the schedule layers +
  each task's ``condition``).
* **Retry / fallback** (from the definition's :class:`RetryPolicy`).
* **Cancellation** (cooperative, via a token checked between groups/tasks).

All collaborators are injected (SOLID/DI) so the engine is fully testable with
simulated agents and no providers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.ai.orchestration.communication.bus import MessageBus
from src.ai.orchestration.communication.messages import MessageType
from src.ai.orchestration.context.context import SharedContext
from src.ai.orchestration.delegation.delegation import DelegationManager
from src.ai.orchestration.events.emitter import EventEmitter
from src.ai.orchestration.events.events import EventType, OrchestrationEvent
from src.ai.orchestration.memory.memory import (
    InMemoryOrchestrationMemory,
    OrchestrationMemory,
)
from src.ai.orchestration.models import (
    AgentOutput,
    Task,
    TaskGraph,
    TaskStatus,
)
from src.ai.orchestration.registry.agent_registry import (
    OrchestrationRegistry,
    orchestration_registry,
)
from src.ai.orchestration.safety.guards import (
    OrchestrationSafetyError,
    OrchestrationSafetyGuard,
)
from src.ai.orchestration.scheduler.scheduler import SchedulePolicy, TaskScheduler
from src.ai.orchestration.state.state import WorkflowState, WorkflowStatus
from src.ai.orchestration.workflow.definition import WorkflowDefinition


class CancellationToken:
    """A cooperative cancellation flag checked between tasks/groups."""

    def __init__(self) -> None:
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        """Return whether cancellation has been requested."""
        return self._cancelled


@dataclass
class WorkflowResult:
    """The outcome of executing a workflow.

    Attributes:
        workflow_id: Run id.
        workflow_name: Executed definition name.
        status: Overall :class:`WorkflowStatus`.
        outputs: ``{task_id: AgentOutput}`` for every task that ran.
        state: The final :class:`WorkflowState` (task/agent records).
        warnings: Soft advisories (safety, fallback, skipped tasks).
        latency_ms: Total wall-clock time.
        error: Populated only for a hard failure/abort.
    """

    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    outputs: dict[str, AgentOutput] = field(default_factory=dict)
    state: WorkflowState | None = None
    warnings: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        """Return ``True`` when the run completed (fully or partially)."""
        return self.status in {WorkflowStatus.COMPLETED, WorkflowStatus.PARTIAL}

    def successful_outputs(self) -> dict[str, AgentOutput]:
        """Return only the outputs whose tasks succeeded."""
        return {tid: o for tid, o in self.outputs.items() if o.ok}


class WorkflowEngine:
    """Runs workflows by orchestrating the framework's layers."""

    _run_counter = 0

    def __init__(
        self,
        *,
        registry: OrchestrationRegistry | None = None,
        delegation: DelegationManager | None = None,
        scheduler: TaskScheduler | None = None,
        safety: OrchestrationSafetyGuard | None = None,
        events: EventEmitter | None = None,
        bus: MessageBus | None = None,
        memory: OrchestrationMemory | None = None,
        schedule_policy: SchedulePolicy | None = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.registry = registry or orchestration_registry
        self.safety = safety or OrchestrationSafetyGuard()
        self.scheduler = scheduler or TaskScheduler(schedule_policy)
        self.delegation = delegation or DelegationManager(self.registry, safety=self.safety)
        # Keep the delegation manager and engine sharing one safety guard.
        self.delegation.safety = self.safety
        self.events = events or EventEmitter()
        self.bus = bus or MessageBus()
        self.memory = memory or InMemoryOrchestrationMemory()

    # -- public API ---------------------------------------------------------

    def run_definition(
        self,
        definition: WorkflowDefinition,
        context: SharedContext | None = None,
        *,
        base_payload: dict | None = None,
        cancellation: CancellationToken | None = None,
    ) -> WorkflowResult:
        """Compile ``definition`` into a graph and execute it."""
        graph = definition.build_graph(base_payload)
        return self.run(
            graph,
            context=context,
            name=definition.name,
            max_retries=definition.retry.max_retries,
            continue_on_failure=definition.retry.continue_on_failure,
            fallback_capability=definition.retry.fallback_capability,
            version=definition.version,
            cancellation=cancellation,
        )

    def run(
        self,
        graph: TaskGraph,
        *,
        context: SharedContext | None = None,
        name: str = "workflow",
        max_retries: int = 1,
        continue_on_failure: bool = True,
        fallback_capability: str | None = None,
        version: str = "v1",
        cancellation: CancellationToken | None = None,
    ) -> WorkflowResult:
        """Execute a validated :class:`TaskGraph` and return a result."""
        workflow_id = self._next_id(name)
        context = context or SharedContext()
        context.workflow_id = workflow_id
        context.current_workflow = name
        cancellation = cancellation or CancellationToken()

        state = WorkflowState(
            workflow_id=workflow_id,
            workflow_name=name,
            status=WorkflowStatus.RUNNING,
            started_at=_now_iso(),
        )
        start = time.perf_counter()

        self._emit(
            EventType.WORKFLOW_STARTED,
            workflow_id,
            message=f"Workflow {name!r} started ({len(graph)} task(s)).",
            data={"version": version, "task_count": len(graph)},
        )

        # Structural safety before anything runs (cycles, size, conflicts).
        try:
            self.safety.validate_graph(graph)
            plan = self.scheduler.schedule(graph)
        except OrchestrationSafetyError as exc:
            return self._abort(state, start, str(exc))

        outputs: dict[str, AgentOutput] = {}
        failed_required = False

        for group in plan.groups:
            if cancellation.cancelled:
                return self._cancel(state, start, outputs)

            for task in group:  # a group is independent → parallel-safe
                if cancellation.cancelled:
                    return self._cancel(state, start, outputs)

                ts = state.task(task.id, task.capability)

                # Conditional execution: skip if the guard key isn't truthy.
                if task.condition and not context.truthy(task.condition):
                    ts.status = TaskStatus.SKIPPED
                    self._emit_task_skipped(workflow_id, task, "condition not met")
                    continue

                # Dependency gate: skip if any *required* dependency failed.
                if self._dependency_failed(task, outputs):
                    ts.status = TaskStatus.SKIPPED
                    self._emit_task_skipped(workflow_id, task, "dependency failed")
                    continue

                output = self._run_task(
                    task,
                    context,
                    state,
                    workflow_id,
                    max_retries=max_retries,
                    fallback_capability=fallback_capability,
                )
                outputs[task.id] = output

                if not output.ok and not task.optional:
                    failed_required = True
                    if not continue_on_failure:
                        state.status = WorkflowStatus.FAILED
                        self._finalize(state, start, outputs, aborted=True)
                        return self._result(state, outputs, start, error=output.error)

        state.status = WorkflowStatus.PARTIAL if failed_required else WorkflowStatus.COMPLETED
        self._finalize(state, start, outputs)
        return self._result(state, outputs, start)

    # -- task execution -----------------------------------------------------

    def _run_task(
        self,
        task: Task,
        context: SharedContext,
        state: WorkflowState,
        workflow_id: str,
        *,
        max_retries: int,
        fallback_capability: str | None,
    ) -> AgentOutput:
        """Delegate one task, applying fallback, events, state and memory."""
        ts = state.task(task.id, task.capability)
        agent = self.delegation.choose(task)
        agent_name = agent.descriptor.name if agent else "(unresolved)"
        ts.mark_running(agent_name)

        self._emit(
            EventType.AGENT_STARTED,
            workflow_id,
            task_id=task.id,
            agent=agent_name,
            message=f"Task {task.id!r} → agent {agent_name!r}.",
            data={"capability": task.capability},
        )
        self.bus.emit(
            MessageType.TASK_REQUEST,
            sender="workflow_engine",
            payload={"task_id": task.id, "capability": task.capability},
            recipient=agent_name,
            correlation_id=workflow_id,
        )

        try:
            output = self.delegation.delegate(task, context, max_retries=max_retries)
        except OrchestrationSafetyError as exc:
            output = AgentOutput(task_id=task.id, agent=agent_name, ok=False, error=str(exc))

        # Config-driven fallback to an alternate capability.
        if not output.ok and fallback_capability:
            fb_task = Task(
                id=task.id,
                goal=task.goal,
                capability=fallback_capability,
                priority=task.priority,
                dependencies=task.dependencies,
                payload=task.payload,
                metadata={**task.metadata, "fallback_for": task.capability},
            )
            fb_output = self.delegation.delegate(fb_task, context, max_retries=0)
            if fb_output.ok:
                fb_output.summary = f"(fallback via {fallback_capability!r}) {fb_output.summary}"
                output = fb_output

        # Record everywhere.
        ts.mark_finished(output)
        state.agent(output.agent).record(output)
        context.record_output(task.id, output.data)
        if task.metadata.get("output_slot"):
            self.safety.claim_output(task.id, task.metadata["output_slot"])
        self.memory.append(
            workflow_id,
            {
                "task_id": task.id,
                "agent": output.agent,
                "ok": output.ok,
                "summary": output.summary,
                "latency_ms": round(output.latency_ms, 2),
            },
        )

        self._emit(
            EventType.AGENT_FINISHED,
            workflow_id,
            task_id=task.id,
            agent=output.agent,
            message=f"Task {task.id!r} finished ({'ok' if output.ok else 'failed'}).",
            data={"latency_ms": output.latency_ms, "error": output.error},
        )
        self.bus.emit(
            MessageType.TASK_RESPONSE if output.ok else MessageType.ERROR_EVENT,
            sender=output.agent,
            payload={"task_id": task.id, "ok": output.ok, "summary": output.summary},
            correlation_id=workflow_id,
        )
        self._emit(
            EventType.TASK_COMPLETED if output.ok else EventType.TASK_FAILED,
            workflow_id,
            task_id=task.id,
            agent=output.agent,
            message=output.summary or (output.error or ""),
            data={"ok": output.ok},
        )
        return output

    # -- helpers ------------------------------------------------------------

    def _dependency_failed(self, task: Task, outputs: dict[str, AgentOutput]) -> bool:
        """Return ``True`` if any *non-optional* dependency of ``task`` failed/absent."""
        for dep in task.dependencies:
            out = outputs.get(dep)
            if out is None or not out.ok:
                return True
        return False

    def _emit(self, type: EventType, workflow_id: str, **kw) -> None:
        """Emit an :class:`OrchestrationEvent` on the emitter."""
        self.events.emit(OrchestrationEvent(type=type, workflow_id=workflow_id, **kw))

    def _emit_task_skipped(self, workflow_id: str, task: Task, reason: str) -> None:
        """Emit a skip as a (non-failing) task-failed event annotated with reason."""
        self._emit(
            EventType.TASK_FAILED,
            workflow_id,
            task_id=task.id,
            message=f"Task {task.id!r} skipped: {reason}.",
            data={"skipped": True, "reason": reason},
        )

    def _finalize(
        self,
        state: WorkflowState,
        start: float,
        outputs: dict[str, AgentOutput],
        *,
        aborted: bool = False,
    ) -> None:
        """Stamp finish time + emit the terminal workflow event."""
        state.finished_at = _now_iso()
        latency = (time.perf_counter() - start) * 1000.0
        for warning in self.safety.warnings:
            self.memory.append(state.workflow_id, {"warning": warning})
        self._emit(
            EventType.WORKFLOW_COMPLETED,
            state.workflow_id,
            message=f"Workflow {state.workflow_name!r} → {state.status.value}.",
            data={
                "status": state.status.value,
                "latency_ms": latency,
                "task_count": len(outputs),
                "aborted": aborted,
            },
        )

    def _result(
        self,
        state: WorkflowState,
        outputs: dict[str, AgentOutput],
        start: float,
        *,
        error: str | None = None,
    ) -> WorkflowResult:
        """Assemble the final :class:`WorkflowResult`."""
        return WorkflowResult(
            workflow_id=state.workflow_id,
            workflow_name=state.workflow_name,
            status=state.status,
            outputs=outputs,
            state=state,
            warnings=self.safety.warnings,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            error=error,
        )

    def _abort(self, state: WorkflowState, start: float, error: str) -> WorkflowResult:
        """Abort a run before/at scheduling on a hard safety violation."""
        state.status = WorkflowStatus.FAILED
        state.finished_at = _now_iso()
        self._emit(
            EventType.WORKFLOW_COMPLETED,
            state.workflow_id,
            message=f"Workflow {state.workflow_name!r} aborted: {error}",
            data={"status": "failed", "error": error},
        )
        return self._result(state, {}, start, error=error)

    def _cancel(
        self, state: WorkflowState, start: float, outputs: dict[str, AgentOutput]
    ) -> WorkflowResult:
        """Handle cooperative cancellation."""
        state.status = WorkflowStatus.CANCELLED
        state.finished_at = _now_iso()
        self._emit(
            EventType.WORKFLOW_CANCELLED,
            state.workflow_id,
            message=f"Workflow {state.workflow_name!r} cancelled.",
            data={"completed": state.completed_ids()},
        )
        return self._result(state, outputs, start, error="Workflow cancelled.")

    @classmethod
    def _next_id(cls, name: str) -> str:
        """Return a process-unique workflow run id."""
        cls._run_counter += 1
        return f"wf_{name}_{cls._run_counter}"


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat(timespec="milliseconds")
