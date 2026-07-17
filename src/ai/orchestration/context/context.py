"""SharedContext — the single context object every agent receives (Module 6).

One workflow run has exactly one :class:`SharedContext`. Agents read the working
state they need (candidate, JD, pipeline, …) and write results back into a shared
scratch space so *later* tasks can consume *earlier* task outputs without any
direct agent-to-agent coupling.

The named slots below are deliberately generic hiring *nouns* (candidate, jd,
comparison, timeline, risk) — they are containers, not behaviour. The framework
never interprets them; only future agents do. Anything not covered by a named
slot lives in :attr:`store`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass
class SharedContext:
    """Mutable, workflow-scoped context shared by all agents in a run.

    Attributes:
        workflow_id: Id of the workflow this context belongs to.
        candidate: Candidate under consideration (opaque to the framework).
        jd: Current job-description text.
        conversation: Prior conversation / turns relevant to the run.
        pipeline: Pipeline state relevant to the run.
        comparison: Comparison set / results.
        timeline: Career-timeline artefacts.
        risk: Risk artefacts.
        current_workflow: Name of the workflow definition being executed.
        outputs: ``{task_id: AgentOutput.data}`` produced so far (read by later tasks).
        store: Free-form key/value scratch space for anything uncategorised.
    """

    workflow_id: str = ""
    candidate: Any = None
    jd: str = ""
    conversation: Any = None
    pipeline: Any = None
    comparison: Any = None
    timeline: Any = None
    risk: Any = None
    current_workflow: str = ""
    outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    store: dict[str, Any] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock, repr=False, compare=False)

    # -- generic scratch space ----------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` in the free-form store (thread-safe)."""
        with self._lock:
            self.store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value for ``key`` (or ``default``)."""
        with self._lock:
            return self.store.get(key, default)

    def has(self, key: str) -> bool:
        """Return ``True`` iff ``key`` is present in named slots or the store."""
        with self._lock:
            named = getattr(self, key, None) if key in _NAMED_SLOTS else None
            return named is not None or key in self.store

    def truthy(self, key: str) -> bool:
        """Return whether ``key`` resolves to a truthy value (for conditions).

        Looks first at the named slots, then the free-form store. Used by the
        workflow engine to evaluate a task's :attr:`Task.condition`.
        """
        with self._lock:
            if key in _NAMED_SLOTS:
                return bool(getattr(self, key))
            return bool(self.store.get(key))

    # -- task output plumbing (later tasks consume earlier ones) ------------

    def record_output(self, task_id: str, data: dict[str, Any]) -> None:
        """Record a completed task's structured output for downstream tasks."""
        with self._lock:
            self.outputs[task_id] = data

    def output_of(self, task_id: str) -> dict[str, Any] | None:
        """Return a previously-recorded task output, or ``None``."""
        with self._lock:
            return self.outputs.get(task_id)

    def dependency_outputs(self, task) -> dict[str, dict[str, Any]]:
        """Return ``{dep_id: output}`` for every dependency of ``task`` that ran."""
        with self._lock:
            return {dep: self.outputs[dep] for dep in task.dependencies if dep in self.outputs}

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the context (for monitoring)."""
        with self._lock:
            named = {slot: _describe(getattr(self, slot)) for slot in _NAMED_SLOTS}
            named.update(
                {
                    "workflow_id": self.workflow_id,
                    "current_workflow": self.current_workflow,
                    "recorded_outputs": sorted(self.outputs.keys()),
                    "store_keys": sorted(self.store.keys()),
                }
            )
            return named


_NAMED_SLOTS: list[str] = [
    "candidate",
    "jd",
    "conversation",
    "pipeline",
    "comparison",
    "timeline",
    "risk",
]


def _describe(value: Any) -> Any:
    """Return a compact, JSON-safe descriptor of a context slot value."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return f"<{type(value).__name__}>"
