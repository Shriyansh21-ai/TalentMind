"""Integration observability (Module 15).

A lightweight, in-memory telemetry surface for the integration platform:
per-integration connection statistics, failure/retry tracking, latency metrics
and a bounded structured-log ring. Everything is offline and deterministic; a
production deployment binds these hooks to a real metrics/logging backend
(Prometheus, OpenTelemetry, Datadog) without changing callers.

Records are keyed by ``(tenant_id, integration_id)`` and are tenant-scoped by
construction — a caller only ever reads the tuples it asks for.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.models import PlatformModel


class LogLevel(str, Enum):
    """Severity of a structured integration log line."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IntegrationLogEntry(PlatformModel):
    """A single structured log line scoped to a tenant + integration."""

    tenant_id: str
    integration_id: str
    level: LogLevel = LogLevel.INFO
    event: str = ""
    message: str = ""
    at: datetime = Field(default_factory=lambda: datetime.min)
    fields: dict[str, object] = Field(default_factory=dict)


class ConnectionStatistics(PlatformModel):
    """Aggregate connection/operation statistics for one integration."""

    tenant_id: str
    integration_id: str
    connect_attempts: int = 0
    connect_successes: int = 0
    connect_failures: int = 0
    operations: int = 0
    failures: int = 0
    retries: int = 0
    total_latency_ms: float = 0.0
    last_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        """Return the fraction of operations that did not fail (0..1)."""
        if self.operations == 0:
            return 1.0
        return (self.operations - self.failures) / self.operations

    @property
    def avg_latency_ms(self) -> float:
        """Return the mean operation latency in milliseconds."""
        if self.operations == 0:
            return 0.0
        return self.total_latency_ms / self.operations


class ObservabilityRegistry:
    """Collects integration telemetry across tenants (in-memory)."""

    def __init__(self, *, clock: Clock | None = None, log_capacity: int = 500) -> None:
        self._clock = clock or SystemClock()
        self._log_capacity = log_capacity
        self._stats: dict[tuple[str, str], ConnectionStatistics] = {}
        self._logs: list[IntegrationLogEntry] = []

    # -- statistics ---------------------------------------------------------

    def stats_for(self, tenant_id: str, integration_id: str) -> ConnectionStatistics:
        """Return (creating if needed) the statistics for one integration."""
        key = (tenant_id, integration_id)
        if key not in self._stats:
            self._stats[key] = ConnectionStatistics(
                tenant_id=tenant_id, integration_id=integration_id
            )
        return self._stats[key]

    def record_connect(self, tenant_id: str, integration_id: str, *, ok: bool) -> None:
        """Record a connection attempt and its outcome."""
        stats = self.stats_for(tenant_id, integration_id)
        stats.connect_attempts += 1
        if ok:
            stats.connect_successes += 1
        else:
            stats.connect_failures += 1

    def record_operation(
        self,
        tenant_id: str,
        integration_id: str,
        *,
        ok: bool = True,
        latency_ms: float = 0.0,
        retried: bool = False,
    ) -> None:
        """Record an operation's outcome, latency and whether it was retried."""
        stats = self.stats_for(tenant_id, integration_id)
        stats.operations += 1
        if not ok:
            stats.failures += 1
        if retried:
            stats.retries += 1
        stats.last_latency_ms = latency_ms
        stats.total_latency_ms += latency_ms
        stats.max_latency_ms = max(stats.max_latency_ms, latency_ms)

    def all_stats(self, *, tenant_id: str | None = None) -> list[ConnectionStatistics]:
        """Return all statistics, optionally filtered to one tenant."""
        values = list(self._stats.values())
        if tenant_id is not None:
            values = [s for s in values if s.tenant_id == tenant_id]
        return values

    # -- logs ---------------------------------------------------------------

    def log(
        self,
        tenant_id: str,
        integration_id: str,
        event: str,
        *,
        level: LogLevel = LogLevel.INFO,
        message: str = "",
        fields: dict[str, object] | None = None,
    ) -> IntegrationLogEntry:
        """Append a structured log line (ring-buffered to ``log_capacity``)."""
        entry = IntegrationLogEntry(
            tenant_id=tenant_id,
            integration_id=integration_id,
            level=level,
            event=event,
            message=message,
            at=self._clock.now(),
            fields=fields or {},
        )
        self._logs.append(entry)
        if len(self._logs) > self._log_capacity:
            self._logs = self._logs[-self._log_capacity :]
        return entry

    def logs(
        self,
        *,
        tenant_id: str | None = None,
        integration_id: str | None = None,
        limit: int = 100,
    ) -> list[IntegrationLogEntry]:
        """Return the most recent log lines, newest first, filtered."""
        rows = self._logs
        if tenant_id is not None:
            rows = [r for r in rows if r.tenant_id == tenant_id]
        if integration_id is not None:
            rows = [r for r in rows if r.integration_id == integration_id]
        return list(reversed(rows[-limit:]))
