"""Resource management & metrics (Module 9).

CPU / memory / disk / queue / worker / AI / connection metrics and platform
utilization, plus a capacity planner. System metrics come from :mod:`psutil`
when it is installed; otherwise the provider reports ``None`` for those fields
(interfaces only where system metrics aren't available) so the runtime never
fabricates numbers it cannot measure. Application metrics (queue depth, workers,
etc.) are supplied by injected getters so this module stays decoupled.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import Field

from src.platform.common.models import PlatformModel

try:  # psutil is optional — system metrics are interfaces-only without it.
    import psutil as _psutil  # type: ignore
except Exception:  # pragma: no cover - import guard
    _psutil = None


class SystemMetrics(PlatformModel):
    """System-level resource sample (``None`` where not measurable offline)."""

    cpu_percent: float | None = None
    memory_percent: float | None = None
    memory_used_mb: float | None = None
    disk_percent: float | None = None
    available: bool = False


class ApplicationMetrics(PlatformModel):
    """Application-level runtime counters."""

    queue_depth: int = 0
    active_workers: int = 0
    total_workers: int = 0
    running_jobs: int = 0
    ai_requests: int = 0
    open_connections: int = 0


class PlatformUtilization(PlatformModel):
    """A combined system + application utilization snapshot."""

    system: SystemMetrics = Field(default_factory=SystemMetrics)
    application: ApplicationMetrics = Field(default_factory=ApplicationMetrics)


class CapacityPlan(PlatformModel):
    """A capacity recommendation derived from current utilization."""

    current_workers: int = 0
    recommended_workers: int = 0
    queue_pressure: float = 0.0  # queue_depth / (workers * per_worker_capacity)
    scale_up: bool = False
    scale_down: bool = False
    rationale: str = ""


@runtime_checkable
class MetricsProvider(Protocol):
    """A source of system-level resource metrics (interface only)."""

    def sample(self) -> SystemMetrics: ...


class NullMetricsProvider:
    """Reports no system metrics — the offline default when psutil is absent."""

    def sample(self) -> SystemMetrics:
        return SystemMetrics(available=False)


class PsutilMetricsProvider:
    """Reads real system metrics from :mod:`psutil` when it is installed."""

    def sample(self) -> SystemMetrics:
        if _psutil is None:
            return SystemMetrics(available=False)
        try:
            vm = _psutil.virtual_memory()
            disk = _psutil.disk_usage("/")
            return SystemMetrics(
                cpu_percent=_psutil.cpu_percent(interval=None),
                memory_percent=vm.percent,
                memory_used_mb=round(vm.used / (1024 * 1024), 1),
                disk_percent=disk.percent,
                available=True,
            )
        except Exception:  # pragma: no cover - defensive
            return SystemMetrics(available=False)


def default_metrics_provider() -> MetricsProvider:
    """Return psutil-backed metrics if available, else a null provider."""
    return PsutilMetricsProvider() if _psutil is not None else NullMetricsProvider()


class ResourceMonitor:
    """Combines system metrics with injected application-metric getters."""

    def __init__(
        self,
        *,
        metrics_provider: MetricsProvider | None = None,
        app_metrics: Callable[[], ApplicationMetrics] | None = None,
    ) -> None:
        self._provider = metrics_provider or default_metrics_provider()
        self._app_metrics = app_metrics or (lambda: ApplicationMetrics())

    def utilization(self) -> PlatformUtilization:
        """Return the combined system + application utilization snapshot."""
        return PlatformUtilization(
            system=self._provider.sample(),
            application=self._app_metrics(),
        )

    def plan_capacity(
        self, *, per_worker_capacity: int = 5, target_pressure: float = 0.7
    ) -> CapacityPlan:
        """Recommend a worker count from queue pressure (no action taken)."""
        app = self._app_metrics()
        workers = max(1, app.active_workers)
        capacity = workers * max(1, per_worker_capacity)
        pressure = app.queue_depth / capacity if capacity else 0.0
        plan = CapacityPlan(
            current_workers=app.active_workers,
            recommended_workers=app.active_workers,
            queue_pressure=round(pressure, 3),
        )
        if pressure > target_pressure:
            needed = -(-app.queue_depth // max(1, int(per_worker_capacity * target_pressure)))
            plan.recommended_workers = max(app.active_workers, needed)
            plan.scale_up = plan.recommended_workers > app.active_workers
            plan.rationale = "queue pressure above target — scale up"
        elif pressure < target_pressure / 3 and app.active_workers > 1:
            plan.recommended_workers = max(1, app.active_workers - 1)
            plan.scale_down = True
            plan.rationale = "queue pressure well below target — scale down"
        else:
            plan.rationale = "within target pressure band"
        return plan
