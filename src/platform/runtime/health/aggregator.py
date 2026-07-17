"""Health aggregator (Module 6).

Registers named health checks (each a callable returning a
:class:`ComponentHealth`) and aggregates them into a single
:class:`HealthReport` whose overall state is the *worst* component state.
Components are decoupled: platform, worker, queue, cache, integration, AI and
database health are all supplied as registered checks, so the aggregator never
imports those subsystems directly. Ready-made builders wire the common runtime
components; database health is an interface placeholder until a driver is bound.
"""

from __future__ import annotations

from collections.abc import Callable

from src.platform.common.clock import Clock, SystemClock
from src.platform.runtime.common.models import HealthState
from src.platform.runtime.health.models import ComponentHealth, HealthReport

#: A health check produces one component's health on demand.
HealthCheck = Callable[[], ComponentHealth]


class HealthAggregator:
    """Registers component health checks and aggregates them."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()
        self._checks: dict[str, HealthCheck] = {}

    def register(self, name: str, check: HealthCheck) -> None:
        """Register a named health check."""
        self._checks[name] = check

    def unregister(self, name: str) -> None:
        """Remove a registered check (no-op if absent)."""
        self._checks.pop(name, None)

    def names(self) -> list[str]:
        """Return the registered component names."""
        return list(self._checks)

    def check(self) -> HealthReport:
        """Run every check and aggregate into a report (worst-state wins)."""
        now = self._clock.now()
        components: list[ComponentHealth] = []
        for name, check in self._checks.items():
            try:
                component = check()
            except Exception as exc:  # a failing check is itself unhealthy
                component = ComponentHealth(
                    name=name,
                    state=HealthState.UNHEALTHY,
                    message=f"health check raised: {exc}",
                )
            component.checked_at = now
            components.append(component)
        overall = HealthState.worst([c.state for c in components])
        return HealthReport(state=overall, components=components, checked_at=now)


# -- ready-made component checks -------------------------------------------


def static_check(name: str, state: HealthState, message: str = "") -> HealthCheck:
    """Return a check that always reports a fixed state (tests / placeholders)."""
    return lambda: ComponentHealth(name=name, state=state, message=message)


def worker_pool_check(name: str, pool) -> HealthCheck:
    """Return a check that derives health from a :class:`WorkerPool`."""

    def _check() -> ComponentHealth:
        metrics = pool.metrics()
        state = pool.health()
        return ComponentHealth(name=name, state=state, details=metrics)

    return _check


def queue_check(name: str, queue, *, capacity_warn_ratio: float = 0.8) -> HealthCheck:
    """Return a check that reports DEGRADED when a queue nears capacity."""

    def _check() -> ComponentHealth:
        depth = len(queue)
        ratio = depth / queue.capacity if queue.capacity else 0.0
        if ratio >= 1.0:
            state = HealthState.UNHEALTHY
        elif ratio >= capacity_warn_ratio:
            state = HealthState.DEGRADED
        else:
            state = HealthState.HEALTHY
        return ComponentHealth(
            name=name,
            state=state,
            details={"depth": depth, "capacity": queue.capacity},
        )

    return _check


def cache_check(name: str, cache_manager) -> HealthCheck:
    """Return a check that reports cache health + hit-rate details."""

    def _check() -> ComponentHealth:
        stats = cache_manager.stats()
        return ComponentHealth(name=name, state=HealthState.HEALTHY, details=stats)

    return _check


def database_check(name: str = "database") -> HealthCheck:
    """Return the database health *interface* placeholder (UNKNOWN offline)."""
    return static_check(name, HealthState.UNKNOWN, "database health interface — no driver bound")
