"""Workflow monitor (Module 11).

Subscribes to the :class:`EventEmitter` and folds the event stream into live
metrics — execution time, per-agent latency, failures, retries, task durations
and success rate — plus a human-readable "visual" workflow log.

The monitor is a pure *observer*: it never mutates a workflow, so attaching or
detaching it can never change an outcome. It is the read model behind the
visualization page (Module 15).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from src.ai.orchestration.events.emitter import EventEmitter
from src.ai.orchestration.events.events import EventType, OrchestrationEvent


@dataclass
class AgentMetrics:
    """Rolling metrics for a single agent."""

    agent: str
    invocations: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Return mean latency per invocation (0 if none)."""
        return self.total_latency_ms / self.invocations if self.invocations else 0.0

    @property
    def success_rate(self) -> float:
        """Return the 0-100 success rate for this agent."""
        if not self.invocations:
            return 0.0
        return 100.0 * (self.invocations - self.failures) / self.invocations


@dataclass
class WorkflowMetrics:
    """Aggregate metrics for one workflow run."""

    workflow_id: str
    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    retries: int = 0
    total_latency_ms: float = 0.0
    log: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Return the 0-100 task success rate for the run."""
        total = self.tasks_completed + self.tasks_failed
        return 100.0 * self.tasks_completed / total if total else 0.0


class WorkflowMonitor:
    """Live metrics + visual log built from the orchestration event stream."""

    _ICONS = {
        EventType.WORKFLOW_STARTED: "🚀",
        EventType.WORKFLOW_COMPLETED: "🏁",
        EventType.WORKFLOW_CANCELLED: "🛑",
        EventType.AGENT_STARTED: "▶️",
        EventType.AGENT_FINISHED: "✅",
        EventType.TASK_CREATED: "➕",
        EventType.TASK_COMPLETED: "✔️",
        EventType.TASK_FAILED: "⚠️",
    }

    def __init__(self) -> None:
        self.agents: dict[str, AgentMetrics] = {}
        self.workflows: dict[str, WorkflowMetrics] = {}
        self._timeline: list[dict[str, object]] = []

    # -- wiring -------------------------------------------------------------

    def attach(self, emitter: EventEmitter) -> Callable[[], None]:
        """Subscribe to all events on ``emitter``; return an unsubscribe callable."""
        return emitter.on("*", self.observe)

    def observe(self, event: OrchestrationEvent) -> None:
        """Fold one event into the metrics + timeline (never raises)."""
        wf = self.workflows.setdefault(
            event.workflow_id, WorkflowMetrics(workflow_id=event.workflow_id)
        )
        data = event.data or {}

        if event.type == EventType.AGENT_STARTED:
            wf.tasks_started += 1
        elif event.type == EventType.AGENT_FINISHED and event.agent:
            metrics = self.agents.setdefault(event.agent, AgentMetrics(agent=event.agent))
            metrics.invocations += 1
            latency = float(data.get("latency_ms", 0.0) or 0.0)
            metrics.total_latency_ms += latency
            wf.total_latency_ms += latency
            if data.get("error"):
                metrics.failures += 1
        elif event.type == EventType.TASK_COMPLETED:
            wf.tasks_completed += 1
        elif event.type == EventType.TASK_FAILED:
            if not data.get("skipped"):
                wf.tasks_failed += 1

        line = f"{self._ICONS.get(event.type, '•')} [{event.timestamp}] {event.message}"
        wf.log.append(line)
        self._timeline.append(event.to_dict())

    # -- read model ---------------------------------------------------------

    def visual_log(self, workflow_id: str) -> list[str]:
        """Return the human-readable event log for a workflow (visual workflow logs)."""
        wf = self.workflows.get(workflow_id)
        return list(wf.log) if wf else []

    def timeline(self) -> list[dict[str, object]]:
        """Return the full ordered event timeline (for the visualization page)."""
        return list(self._timeline)

    def summary(self) -> dict[str, object]:
        """Return an aggregate snapshot across every observed run."""
        total_started = sum(w.tasks_started for w in self.workflows.values())
        total_completed = sum(w.tasks_completed for w in self.workflows.values())
        total_failed = sum(w.tasks_failed for w in self.workflows.values())
        denom = total_completed + total_failed
        return {
            "workflows": len(self.workflows),
            "tasks_started": total_started,
            "tasks_completed": total_completed,
            "tasks_failed": total_failed,
            "success_rate": round(100.0 * total_completed / denom, 1) if denom else 0.0,
            "agents": {
                name: {
                    "invocations": m.invocations,
                    "failures": m.failures,
                    "avg_latency_ms": round(m.avg_latency_ms, 2),
                    "success_rate": round(m.success_rate, 1),
                }
                for name, m in sorted(self.agents.items())
            },
        }
