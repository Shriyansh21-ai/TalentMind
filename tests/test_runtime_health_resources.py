"""Modules 5, 6 & 9 tests — performance, health monitoring and resources.

Performance: lazy loading, object pooling, cache warming, batch loading, profile
builder. Health: aggregator worst-state-wins and component checks. Resources:
utilization snapshot and capacity planning.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.runtime.cache import CacheManager
from src.platform.runtime.common.models import HealthState
from src.platform.runtime.health import (
    HealthAggregator,
    cache_check,
    database_check,
    queue_check,
    static_check,
    worker_pool_check,
)
from src.platform.runtime.jobs import JobQueue
from src.platform.runtime.performance import (
    BatchLoader,
    CacheWarmer,
    LazyLoader,
    ObjectPool,
    PerformanceProfileBuilder,
)
from src.platform.runtime.resources import ApplicationMetrics, ResourceMonitor
from src.platform.runtime.workers import WorkerPool


# -- performance ------------------------------------------------------------


def test_lazy_loader_computes_once():
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return 42

    lazy = LazyLoader(factory)
    assert not lazy.loaded
    assert lazy.get() == 42
    assert lazy.get() == 42
    assert calls["n"] == 1 and lazy.loaded


def test_object_pool_reuses_objects():
    pool = ObjectPool(lambda: object(), max_size=2)
    a = pool.acquire()
    pool.release(a)
    b = pool.acquire()
    assert a is b  # reused
    assert pool.stats["created"] == 1


def test_cache_warmer_prepopulates():
    manager = CacheManager(clock=FrozenClock())
    warmer = CacheWarmer(manager.analytics_cache)
    warmed = warmer.warm(["a", "b"], lambda k: k.upper())
    assert warmed == 2
    assert manager.analytics_cache.get("a") == "A"


def test_batch_loader_resolves_in_one_call():
    calls = {"n": 0}

    def batch(keys):
        calls["n"] += 1
        return {k: k * 2 for k in keys}

    loader = BatchLoader(batch)
    loader.enqueue("a")
    loader.enqueue("b")
    result = loader.load()
    assert result == {"a": "aa", "b": "bb"}
    assert calls["n"] == 1


def test_performance_profile_builder():
    profile = (
        PerformanceProfileBuilder("bulk")
        .with_batch_size(500)
        .with_pool_size(32)
        .with_cache_warming(True)
        .build()
    )
    assert profile.name == "bulk"
    assert profile.batch_size == 500
    assert profile.pool_size == 32
    assert profile.cache_warming


# -- health -----------------------------------------------------------------


def test_aggregator_worst_state_wins():
    aggregator = HealthAggregator(clock=FrozenClock())
    aggregator.register("a", static_check("a", HealthState.HEALTHY))
    aggregator.register("b", static_check("b", HealthState.DEGRADED))
    report = aggregator.check()
    assert report.state == HealthState.DEGRADED
    assert {c.name for c in report.components} == {"a", "b"}


def test_failing_check_is_unhealthy():
    aggregator = HealthAggregator(clock=FrozenClock())

    def boom():
        raise RuntimeError("check failed")

    aggregator.register("bad", boom)
    report = aggregator.check()
    assert report.state == HealthState.UNHEALTHY


def test_component_check_builders():
    clock = FrozenClock()
    aggregator = HealthAggregator(clock=clock)
    pool = WorkerPool(clock=clock)
    pool.register(name="w1")
    queue = JobQueue(capacity=10)
    cache = CacheManager(clock=clock)
    aggregator.register("workers", worker_pool_check("workers", pool))
    aggregator.register("queue", queue_check("queue", queue))
    aggregator.register("cache", cache_check("cache", cache))
    aggregator.register("database", database_check())
    report = aggregator.check()
    assert report.component("workers").state == HealthState.HEALTHY
    assert report.component("database").state == HealthState.UNKNOWN


# -- resources --------------------------------------------------------------


def test_resource_monitor_reports_application_metrics():
    monitor = ResourceMonitor(
        app_metrics=lambda: ApplicationMetrics(queue_depth=5, active_workers=2)
    )
    util = monitor.utilization()
    assert util.application.queue_depth == 5
    assert util.application.active_workers == 2


def test_capacity_plan_recommends_scale_up():
    monitor = ResourceMonitor(
        app_metrics=lambda: ApplicationMetrics(queue_depth=100, active_workers=2)
    )
    plan = monitor.plan_capacity(per_worker_capacity=5, target_pressure=0.7)
    assert plan.scale_up
    assert plan.recommended_workers > 2
