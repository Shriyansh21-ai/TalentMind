"""Orchestration memory interfaces (Module 7).

Extends the platform's memory idea (:class:`~src.ai.memory.base.BaseMemory`) into
the four orchestration-scoped stores the brief calls for, plus a *designed-only*
long-term interface. Per the brief we deliberately **do not** implement vector
memory yet — the contracts are defined so a future milestone can drop in a
durable / embedding-backed implementation behind them without touching agents.

Scopes:
    WorkflowMemory   — facts about a single workflow run (keyed by workflow id)
    SharedAgentMemory— cross-agent scratch shared within a run
    TaskMemory       — per-task working notes
    ExecutionMemory  — append-only execution trace (durable audit)
    LongTermMemory   — INTERFACE ONLY (future: durable/semantic recall)

:class:`InMemoryOrchestrationMemory` is the reference implementation used by the
engine, the UI and tests — entirely in-process, no I/O.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from threading import RLock
from typing import Any


class WorkflowMemory(ABC):
    """Key/value memory scoped to a single workflow run."""

    @abstractmethod
    def remember(self, workflow_id: str, key: str, value: Any) -> None:
        """Store ``value`` under ``(workflow_id, key)``."""

    @abstractmethod
    def recall(self, workflow_id: str, key: str, default: Any = None) -> Any:
        """Return the stored value for ``(workflow_id, key)``."""

    @abstractmethod
    def dump(self, workflow_id: str) -> dict[str, Any]:
        """Return all facts remembered for ``workflow_id``."""


class SharedAgentMemory(ABC):
    """Scratch space shared by all agents within a run (namespaced by scope)."""

    @abstractmethod
    def share(self, scope: str, key: str, value: Any) -> None:
        """Publish ``value`` under ``(scope, key)`` for other agents to read."""

    @abstractmethod
    def read(self, scope: str, key: str, default: Any = None) -> Any:
        """Read a shared value."""


class TaskMemory(ABC):
    """Per-task working notes (keyed by task id)."""

    @abstractmethod
    def note(self, task_id: str, value: Any) -> None:
        """Append a working note for ``task_id``."""

    @abstractmethod
    def notes(self, task_id: str) -> list[Any]:
        """Return the ordered notes for ``task_id``."""


class ExecutionMemory(ABC):
    """Append-only execution trace (a durable audit of what happened)."""

    @abstractmethod
    def append(self, workflow_id: str, entry: dict[str, Any]) -> None:
        """Append one trace ``entry`` for ``workflow_id``."""

    @abstractmethod
    def trace(self, workflow_id: str) -> list[dict[str, Any]]:
        """Return the ordered trace for ``workflow_id``."""


class LongTermMemory(ABC):
    """Designed-only interface for future durable / semantic recall (Module 7).

    Intentionally unimplemented this milestone. A future milestone can back this
    with a vector store; the orchestrator already depends only on the interface.
    """

    @abstractmethod
    def store(self, namespace: str, key: str, value: Any, *, embedding=None) -> None:
        """Persist a memory (optionally with a precomputed embedding)."""

    @abstractmethod
    def search(self, namespace: str, query: str, *, top_k: int = 5) -> list[Any]:
        """Semantic recall — NOT implemented this milestone."""


class OrchestrationMemory(WorkflowMemory, SharedAgentMemory, TaskMemory, ExecutionMemory, ABC):
    """Aggregate facade combining the four active memory scopes.

    The engine depends on this single interface; the four ABCs above document
    each scope's contract and let a future implementation specialise one scope
    (e.g. a durable :class:`ExecutionMemory`) without changing callers.
    """


class InMemoryOrchestrationMemory(OrchestrationMemory):
    """Thread-safe, in-process reference implementation of all active scopes."""

    def __init__(self) -> None:
        self._workflow: dict[str, dict[str, Any]] = defaultdict(dict)
        self._shared: dict[str, dict[str, Any]] = defaultdict(dict)
        self._tasks: dict[str, list[Any]] = defaultdict(list)
        self._trace: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._lock = RLock()

    # WorkflowMemory --------------------------------------------------------

    def remember(self, workflow_id: str, key: str, value: Any) -> None:
        """Store ``value`` under ``(workflow_id, key)``."""
        with self._lock:
            self._workflow[workflow_id][key] = value

    def recall(self, workflow_id: str, key: str, default: Any = None) -> Any:
        """Return the stored value for ``(workflow_id, key)``."""
        with self._lock:
            return self._workflow[workflow_id].get(key, default)

    def dump(self, workflow_id: str) -> dict[str, Any]:
        """Return a copy of all facts remembered for ``workflow_id``."""
        with self._lock:
            return dict(self._workflow[workflow_id])

    # SharedAgentMemory -----------------------------------------------------

    def share(self, scope: str, key: str, value: Any) -> None:
        """Publish ``value`` under ``(scope, key)``."""
        with self._lock:
            self._shared[scope][key] = value

    def read(self, scope: str, key: str, default: Any = None) -> Any:
        """Read a shared value."""
        with self._lock:
            return self._shared[scope].get(key, default)

    # TaskMemory ------------------------------------------------------------

    def note(self, task_id: str, value: Any) -> None:
        """Append a working note for ``task_id``."""
        with self._lock:
            self._tasks[task_id].append(value)

    def notes(self, task_id: str) -> list[Any]:
        """Return the ordered notes for ``task_id``."""
        with self._lock:
            return list(self._tasks[task_id])

    # ExecutionMemory -------------------------------------------------------

    def append(self, workflow_id: str, entry: dict[str, Any]) -> None:
        """Append one trace ``entry`` for ``workflow_id``."""
        with self._lock:
            self._trace[workflow_id].append(entry)

    def trace(self, workflow_id: str) -> list[dict[str, Any]]:
        """Return the ordered trace for ``workflow_id``."""
        with self._lock:
            return list(self._trace[workflow_id])
