"""Observability models (Module 5).

Unified telemetry types spanning logs, metrics and distributed traces, tied
together by correlation / request / span / trace ids. These are the
OpenTelemetry-shaped value objects a unified observability service produces; the
export seams (OpenTelemetry / Prometheus / Grafana) are interfaces only.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel


class LogLevel(str, Enum):
    """Severity of a log record."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """The kind of metric being recorded."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class LogRecord(PlatformModel):
    """A structured, correlated log record."""

    level: LogLevel = LogLevel.INFO
    message: str = ""
    source: str = ""
    tenant_id: str | None = None
    correlation_id: str = ""
    request_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    at: datetime = Field(default_factory=lambda: datetime.min)
    attributes: dict[str, object] = Field(default_factory=dict)


class Metric(PlatformModel):
    """A single metric sample."""

    name: str
    metric_type: MetricType = MetricType.COUNTER
    value: float = 0.0
    labels: dict[str, str] = Field(default_factory=dict)
    at: datetime = Field(default_factory=lambda: datetime.min)


class SpanStatus(str, Enum):
    """The status of a completed span."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


class Span(PlatformModel):
    """A single span within a distributed trace."""

    span_id: str
    trace_id: str
    parent_span_id: str = ""
    name: str = ""
    source: str = ""
    started_at: datetime
    ended_at: datetime | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, object] = Field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Return the span duration in milliseconds (0 if not ended)."""
        if self.ended_at is None:
            return 0.0
        return (self.ended_at - self.started_at).total_seconds() * 1000.0


class Trace(PlatformModel):
    """A distributed trace: an ordered set of spans sharing a trace id."""

    trace_id: str
    spans: list[Span] = Field(default_factory=list)

    @property
    def root(self) -> Span | None:
        """Return the root span (the one with no parent), if present."""
        return next((s for s in self.spans if not s.parent_span_id), None)

    @property
    def duration_ms(self) -> float:
        """Return the total trace duration across its spans."""
        return sum(s.duration_ms for s in self.spans)
