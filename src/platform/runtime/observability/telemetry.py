"""Observability runtime (Module 13).

Structured runtime logs plus latency/execution/failure/resource metrics, and an
OpenTelemetry-ready tracing seam (:class:`Tracer` / :class:`Span`) with a no-op
default. Everything is in-memory and offline; a production deployment binds the
tracer and metric sinks to a real backend (OpenTelemetry, Prometheus) without
changing callers. No vendor integration ships.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.models import PlatformModel
from src.platform.runtime.common.models import Severity


class RuntimeLogEntry(PlatformModel):
    """A structured runtime log line scoped to a component."""

    component: str
    event: str = ""
    severity: Severity = Severity.INFO
    message: str = ""
    tenant_id: str | None = None
    at: datetime = Field(default_factory=lambda: datetime.min)
    fields: dict[str, object] = Field(default_factory=dict)


class LatencyStats(PlatformModel):
    """Aggregate latency statistics for a named metric."""

    name: str
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    last_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        """Return the mean latency in milliseconds."""
        return self.total_ms / self.count if self.count else 0.0


class ExecutionCounter(PlatformModel):
    """Success/failure counters for a named execution surface."""

    name: str
    executions: int = 0
    failures: int = 0

    @property
    def success_rate(self) -> float:
        """Return the fraction of executions that did not fail (0..1)."""
        if self.executions == 0:
            return 1.0
        return (self.executions - self.failures) / self.executions


@runtime_checkable
class Span(Protocol):
    """A tracing span (OpenTelemetry-shaped, minimal surface)."""

    def set_attribute(self, key: str, value: object) -> None: ...
    def end(self) -> None: ...


@runtime_checkable
class Tracer(Protocol):
    """A tracer that starts spans (OpenTelemetry-ready seam)."""

    def start_span(self, name: str) -> Span: ...


class _NoOpSpan:
    """A span that records attributes but does nothing else (offline default)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, object] = {}
        self.ended = False

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        self.ended = True


class NoOpTracer:
    """The default tracer — creates in-memory spans, exports nothing."""

    def start_span(self, name: str) -> _NoOpSpan:
        return _NoOpSpan(name)


class RuntimeTelemetry:
    """In-memory runtime logs + metrics with an OpenTelemetry-ready tracer."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        tracer: Tracer | None = None,
        log_capacity: int = 1000,
    ) -> None:
        self._clock = clock or SystemClock()
        self.tracer: Tracer = tracer or NoOpTracer()
        self._log_capacity = log_capacity
        self._logs: list[RuntimeLogEntry] = []
        self._latency: dict[str, LatencyStats] = {}
        self._exec: dict[str, ExecutionCounter] = {}

    # -- logs ---------------------------------------------------------------

    def log(
        self,
        component: str,
        event: str,
        *,
        severity: Severity = Severity.INFO,
        message: str = "",
        tenant_id: str | None = None,
        fields: dict[str, object] | None = None,
    ) -> RuntimeLogEntry:
        """Append a structured log line (ring-buffered to ``log_capacity``)."""
        entry = RuntimeLogEntry(
            component=component,
            event=event,
            severity=severity,
            message=message,
            tenant_id=tenant_id,
            at=self._clock.now(),
            fields=fields or {},
        )
        self._logs.append(entry)
        if len(self._logs) > self._log_capacity:
            self._logs = self._logs[-self._log_capacity :]
        return entry

    def logs(
        self, *, component: str | None = None, limit: int = 100
    ) -> list[RuntimeLogEntry]:
        """Return the most recent log lines, newest first, filtered."""
        rows = self._logs
        if component is not None:
            rows = [r for r in rows if r.component == component]
        return list(reversed(rows[-limit:]))

    # -- metrics ------------------------------------------------------------

    def record_latency(self, name: str, ms: float) -> None:
        """Record a latency sample for ``name``."""
        stats = self._latency.setdefault(name, LatencyStats(name=name))
        stats.count += 1
        stats.total_ms += ms
        stats.last_ms = ms
        stats.max_ms = max(stats.max_ms, ms)

    def record_execution(self, name: str, *, ok: bool = True) -> None:
        """Record an execution outcome for ``name``."""
        counter = self._exec.setdefault(name, ExecutionCounter(name=name))
        counter.executions += 1
        if not ok:
            counter.failures += 1

    def latency(self) -> list[LatencyStats]:
        """Return all latency statistics."""
        return list(self._latency.values())

    def executions(self) -> list[ExecutionCounter]:
        """Return all execution counters."""
        return list(self._exec.values())

    @contextmanager
    def span(self, name: str) -> Iterator[Span]:
        """Context manager that opens a tracing span and records its latency."""
        started = self._clock.now().timestamp()
        active = self.tracer.start_span(name)
        try:
            yield active
        finally:
            active.end()
            elapsed_ms = (self._clock.now().timestamp() - started) * 1000.0
            self.record_latency(name, elapsed_ms)
