"""Module 2 tests — worker framework.

Registration, lifecycle transitions, heartbeat health (stale → UNHEALTHY →
revived), horizontal scaling, graceful shutdown/drain and aggregate metrics.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.runtime.common.errors import WorkerError
from src.platform.runtime.common.models import HealthState
from src.platform.runtime.workers import WorkerPool, WorkerStatus


def test_register_becomes_idle():
    pool = WorkerPool(clock=FrozenClock())
    worker = pool.register(name="w1")
    assert worker.status == WorkerStatus.IDLE
    assert pool.available_worker().id == worker.id


def test_busy_idle_lifecycle_updates_metrics():
    pool = WorkerPool(clock=FrozenClock())
    worker = pool.register(name="w1")
    pool.mark_busy(worker.id, "job-1")
    assert pool.get(worker.id).status == WorkerStatus.BUSY
    pool.mark_idle(worker.id)
    assert pool.get(worker.id).status == WorkerStatus.IDLE
    assert pool.get(worker.id).metrics.jobs_processed == 1


def test_stale_heartbeat_marks_unhealthy_then_revives():
    clock = FrozenClock()
    pool = WorkerPool(heartbeat_timeout_seconds=60, clock=clock)
    worker = pool.register(name="w1")
    clock.advance(seconds=61)
    assert pool.check_health()[worker.id] == HealthState.UNHEALTHY
    assert pool.get(worker.id).status == WorkerStatus.UNHEALTHY
    pool.heartbeat(worker.id)
    assert pool.get(worker.id).status == WorkerStatus.IDLE


def test_scale_up_and_down():
    pool = WorkerPool(clock=FrozenClock())
    pool.scale_to(4)
    assert len(pool.active_workers()) == 4
    pool.scale_to(2)
    assert len(pool.active_workers()) == 2


def test_graceful_drain_of_busy_worker():
    pool = WorkerPool(clock=FrozenClock())
    worker = pool.register(name="w1")
    pool.mark_busy(worker.id, "job-1")
    pool.drain(worker.id)
    assert pool.get(worker.id).status == WorkerStatus.DRAINING
    # Finishing the in-flight job stops the draining worker.
    pool.mark_idle(worker.id)
    assert pool.get(worker.id).status == WorkerStatus.STOPPED


def test_unknown_worker_raises():
    pool = WorkerPool(clock=FrozenClock())
    with pytest.raises(WorkerError):
        pool.get("nope")


def test_pool_metrics_aggregate():
    pool = WorkerPool(clock=FrozenClock())
    a = pool.register(name="a")
    pool.register(name="b")
    pool.mark_busy(a.id, "job-1")
    metrics = pool.metrics()
    assert metrics["total"] == 2
    assert metrics["busy"] == 1
    assert metrics["idle"] == 1
