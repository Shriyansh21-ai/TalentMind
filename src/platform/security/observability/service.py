"""Unified observability service (Module 5).

Collects logs, metrics and distributed spans in one place, correlates them by
correlation / trace id, and assembles traces on demand. Export is delegated to
interface-only provider seams (OpenTelemetry / Prometheus / Grafana) with no-op
defaults — no vendor implementation ships. Deterministic and clock-driven.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Protocol, runtime_checkable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.security.observability.models import (
    LogLevel,
    LogRecord,
    Metric,
    MetricType,
    Span,
    SpanStatus,
    Trace,
)


@runtime_checkable
class TelemetryExporter(Protocol):
    """A telemetry export backend seam (interface only)."""

    name: str

    def export_logs(self, logs: list[LogRecord]) -> None: ...
    def export_metrics(self, metrics: list[Metric]) -> None: ...
    def export_traces(self, traces: list[Trace]) -> None: ...


class _NoOpExporter:
    """The default exporter — records intent, exports nothing (offline)."""

    def __init__(self, name: str) -> None:
        self.name = name

    def export_logs(self, logs: list[LogRecord]) -> None:  # pragma: no cover - noop
        return None

    def export_metrics(self, metrics: list[Metric]) -> None:  # pragma: no cover
        return None

    def export_traces(self, traces: list[Trace]) -> None:  # pragma: no cover
        return None


class OpenTelemetryExporter(_NoOpExporter):
    """OpenTelemetry export seam (interface only)."""

    def __init__(self) -> None:
        super().__init__("opentelemetry")


class PrometheusExporter(_NoOpExporter):
    """Prometheus metrics export seam (interface only)."""

    def __init__(self) -> None:
        super().__init__("prometheus")


class GrafanaExporter(_NoOpExporter):
    """Grafana dashboard/datasource seam (interface only)."""

    def __init__(self) -> None:
        super().__init__("grafana")


class ObservabilityService:
    """Unified logs + metrics + traces with correlation and export seams."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        exporter: TelemetryExporter | None = None,
        capacity: int = 2000,
    ) -> None:
        self._clock = clock or SystemClock()
        self.exporter: TelemetryExporter = exporter or _NoOpExporter("noop")
        self._capacity = capacity
        self._logs: list[LogRecord] = []
        self._metrics: list[Metric] = []
        self._spans: list[Span] = []

    # -- ids ----------------------------------------------------------------

    def new_correlation_id(self) -> str:
        """Mint a new correlation id for a logical operation."""
        return generate_id("corr")

    def new_trace_id(self) -> str:
        """Mint a new trace id."""
        return generate_id("trace")

    # -- logs ---------------------------------------------------------------

    def log(
        self,
        message: str,
        *,
        level: LogLevel = LogLevel.INFO,
        source: str = "",
        tenant_id: str | None = None,
        correlation_id: str = "",
        request_id: str = "",
        trace_id: str = "",
        span_id: str = "",
        attributes: dict[str, object] | None = None,
    ) -> LogRecord:
        """Record a correlated log line."""
        record = LogRecord(
            level=level,
            message=message,
            source=source,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
            at=self._clock.now(),
            attributes=attributes or {},
        )
        self._logs.append(record)
        self._trim()
        return record

    # -- metrics ------------------------------------------------------------

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        metric_type: MetricType = MetricType.COUNTER,
        labels: dict[str, str] | None = None,
    ) -> Metric:
        """Record a metric sample."""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {},
            at=self._clock.now(),
        )
        self._metrics.append(metric)
        self._trim()
        return metric

    # -- traces -------------------------------------------------------------

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str = "",
        parent_span_id: str = "",
        source: str = "",
    ) -> Iterator[Span]:
        """Open a span, record it on exit, and roll it into its trace."""
        started = self._clock.now()
        span = Span(
            span_id=generate_id("span"),
            trace_id=trace_id or self.new_trace_id(),
            parent_span_id=parent_span_id,
            name=name,
            source=source,
            started_at=started,
        )
        try:
            yield span
            span.status = SpanStatus.OK
        except Exception:
            span.status = SpanStatus.ERROR
            raise
        finally:
            span.ended_at = self._clock.now()
            self._spans.append(span)
            self._trim()

    def trace(self, trace_id: str) -> Trace:
        """Assemble the :class:`Trace` for a trace id from recorded spans."""
        spans = [s for s in self._spans if s.trace_id == trace_id]
        return Trace(trace_id=trace_id, spans=spans)

    # -- query & correlation ------------------------------------------------

    def logs(self, *, correlation_id: str | None = None, limit: int = 200) -> list[LogRecord]:
        """Return recent logs, newest first, optionally by correlation id."""
        rows = self._logs
        if correlation_id is not None:
            rows = [r for r in rows if r.correlation_id == correlation_id]
        return list(reversed(rows[-limit:]))

    def metrics(self, *, name: str | None = None) -> list[Metric]:
        """Return recorded metrics, optionally filtered by name."""
        if name is None:
            return list(self._metrics)
        return [m for m in self._metrics if m.name == name]

    def correlate(self, correlation_id: str) -> dict[str, object]:
        """Return all telemetry sharing a correlation id."""
        logs = [r for r in self._logs if r.correlation_id == correlation_id]
        trace_ids = {r.trace_id for r in logs if r.trace_id}
        spans = [s for s in self._spans if s.trace_id in trace_ids]
        return {"logs": logs, "spans": spans}

    def export(self) -> None:
        """Push all collected telemetry to the configured exporter."""
        self.exporter.export_logs(self._logs)
        self.exporter.export_metrics(self._metrics)
        trace_ids = {s.trace_id for s in self._spans}
        self.exporter.export_traces([self.trace(t) for t in trace_ids])

    def _trim(self) -> None:
        if len(self._logs) > self._capacity:
            self._logs = self._logs[-self._capacity :]
        if len(self._metrics) > self._capacity:
            self._metrics = self._metrics[-self._capacity :]
        if len(self._spans) > self._capacity:
            self._spans = self._spans[-self._capacity :]
