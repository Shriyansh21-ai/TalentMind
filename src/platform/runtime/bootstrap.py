"""Runtime platform composition root (Module 14 · Module 18).

Wires the Enterprise Runtime Platform into one lazily-constructed
:class:`RuntimePlatform` facade using the shared
:class:`~src.platform.container.Container`. Every service shares a single
injected :class:`Clock`, one :class:`RuntimeTelemetry`, one
:class:`RuntimeEventPublisher` (over the Milestone 2 event bus) and one
:class:`HealthAggregator` pre-wired with checks for the queue, workers, cache
and resources. Services are lazy singletons built at most once.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.common.clock import Clock, SystemClock
from src.platform.container import Container
from src.platform.integrations.events.bus import EnterpriseEventBus
from src.platform.runtime.cache.manager import CacheManager
from src.platform.runtime.common.models import HealthState
from src.platform.runtime.events.events import RuntimeEventPublisher
from src.platform.runtime.execution.engine import TaskExecutionEngine
from src.platform.runtime.health.aggregator import (
    HealthAggregator,
    cache_check,
    database_check,
    queue_check,
    static_check,
    worker_pool_check,
)
from src.platform.runtime.jobs.manager import JobManager
from src.platform.runtime.jobs.models import JobStatus
from src.platform.runtime.load.manager import LoadManager
from src.platform.runtime.observability.telemetry import RuntimeTelemetry
from src.platform.runtime.resilience.engine import ResilienceEngine
from src.platform.runtime.resources.metrics import ApplicationMetrics, ResourceMonitor
from src.platform.runtime.services.background import (
    BackgroundServiceManager,
    cache_cleanup_task,
    health_polling_task,
    telemetry_cleanup_task,
)
from src.platform.runtime.workers.pool import WorkerPool


@dataclass
class RuntimePlatform:
    """A fully-wired runtime platform exposing every module's service."""

    container: Container
    clock: Clock

    @property
    def telemetry(self) -> RuntimeTelemetry:
        return self.container.resolve("runtime.telemetry")  # type: ignore[return-value]

    @property
    def events(self) -> RuntimeEventPublisher:
        return self.container.resolve("runtime.events")  # type: ignore[return-value]

    @property
    def jobs(self) -> JobManager:
        return self.container.resolve("runtime.jobs")  # type: ignore[return-value]

    @property
    def workers(self) -> WorkerPool:
        return self.container.resolve("runtime.workers")  # type: ignore[return-value]

    @property
    def execution(self) -> TaskExecutionEngine:
        return self.container.resolve("runtime.execution")  # type: ignore[return-value]

    @property
    def cache(self) -> CacheManager:
        return self.container.resolve("runtime.cache")  # type: ignore[return-value]

    @property
    def resilience(self) -> ResilienceEngine:
        return self.container.resolve("runtime.resilience")  # type: ignore[return-value]

    @property
    def load(self) -> LoadManager:
        return self.container.resolve("runtime.load")  # type: ignore[return-value]

    @property
    def resources(self) -> ResourceMonitor:
        return self.container.resolve("runtime.resources")  # type: ignore[return-value]

    @property
    def health(self) -> HealthAggregator:
        return self.container.resolve("runtime.health")  # type: ignore[return-value]

    @property
    def services(self) -> BackgroundServiceManager:
        return self.container.resolve("runtime.services")  # type: ignore[return-value]


def build_runtime_platform(
    *,
    clock: Clock | None = None,
    event_bus: EnterpriseEventBus | None = None,
) -> RuntimePlatform:
    """Compose and return a fully-wired :class:`RuntimePlatform`."""
    the_clock = clock or SystemClock()
    container = Container()

    container.register("runtime.telemetry", lambda _c: RuntimeTelemetry(clock=the_clock))
    container.register(
        "runtime.events",
        lambda _c: RuntimeEventPublisher(event_bus, clock=the_clock),
    )
    container.register("runtime.resilience", lambda _c: ResilienceEngine(clock=the_clock))

    container.register(
        "runtime.jobs",
        lambda c: JobManager(
            telemetry=c.resolve("runtime.telemetry"),  # type: ignore[arg-type]
            events=c.resolve("runtime.events"),  # type: ignore[arg-type]
            clock=the_clock,
        ),
    )
    container.register(
        "runtime.workers",
        lambda c: WorkerPool(events=c.resolve("runtime.events"), clock=the_clock),  # type: ignore[arg-type]
    )
    container.register(
        "runtime.execution",
        lambda c: TaskExecutionEngine(
            resilience=c.resolve("runtime.resilience"),  # type: ignore[arg-type]
            telemetry=c.resolve("runtime.telemetry"),  # type: ignore[arg-type]
            clock=the_clock,
        ),
    )
    container.register("runtime.cache", lambda _c: CacheManager(clock=the_clock))
    container.register("runtime.load", lambda _c: LoadManager(clock=the_clock))

    def _resources(c: Container) -> ResourceMonitor:
        jobs: JobManager = c.resolve("runtime.jobs")  # type: ignore[assignment]
        workers: WorkerPool = c.resolve("runtime.workers")  # type: ignore[assignment]

        def app_metrics() -> ApplicationMetrics:
            running = jobs.repo.list(where=lambda j: j.status == JobStatus.RUNNING)
            return ApplicationMetrics(
                queue_depth=len(jobs.queue),
                active_workers=len(workers.active_workers()),
                total_workers=len(workers.workers()),
                running_jobs=len(running),
            )

        return ResourceMonitor(app_metrics=app_metrics)

    container.register("runtime.resources", _resources)

    def _health(c: Container) -> HealthAggregator:
        jobs: JobManager = c.resolve("runtime.jobs")  # type: ignore[assignment]
        workers: WorkerPool = c.resolve("runtime.workers")  # type: ignore[assignment]
        cache: CacheManager = c.resolve("runtime.cache")  # type: ignore[assignment]
        aggregator = HealthAggregator(clock=the_clock)
        aggregator.register(
            "platform", static_check("platform", HealthState.HEALTHY, "runtime operational")
        )
        aggregator.register("workers", worker_pool_check("workers", workers))
        aggregator.register("queue", queue_check("queue", jobs.queue))
        aggregator.register("cache", cache_check("cache", cache))
        aggregator.register(
            "integration",
            static_check("integration", HealthState.HEALTHY, "integration platform reachable"),
        )
        aggregator.register(
            "ai_platform",
            static_check("ai_platform", HealthState.HEALTHY, "ai platform reachable"),
        )
        aggregator.register("database", database_check())
        return aggregator

    container.register("runtime.health", _health)

    def _services(c: Container) -> BackgroundServiceManager:
        manager = BackgroundServiceManager(clock=the_clock)
        cache: CacheManager = c.resolve("runtime.cache")  # type: ignore[assignment]
        telemetry: RuntimeTelemetry = c.resolve("runtime.telemetry")  # type: ignore[assignment]
        aggregator: HealthAggregator = c.resolve("runtime.health")  # type: ignore[assignment]
        manager.register("cache_cleanup", 300.0, cache_cleanup_task(cache))
        manager.register("telemetry_cleanup", 600.0, telemetry_cleanup_task(telemetry))
        manager.register("health_polling", 30.0, health_polling_task(aggregator))
        return manager

    container.register("runtime.services", _services)

    return RuntimePlatform(container=container, clock=the_clock)
