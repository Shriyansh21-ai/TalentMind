"""Module 1 tests — background job platform.

Registry, priority queue (ordering + overflow), scheduler, and the job manager
lifecycle: submit, dependencies (block/unblock/fail), claim, complete, retry,
cancellation and tenant isolation.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.common.errors import TenantIsolationError
from src.platform.runtime.common.errors import QueueOverflowError, RuntimeValidationError
from src.platform.runtime.jobs import (
    Job,
    JobDefinition,
    JobManager,
    JobPriority,
    JobQueue,
    JobStatus,
)
from src.platform.runtime.jobs.scheduler import JobScheduler
from src.platform.runtime.resilience import RetryPolicy


def _manager() -> JobManager:
    clock = FrozenClock()
    manager = JobManager(clock=clock)
    manager.define(
        JobDefinition(
            id="d1", key="reindex", name="Reindex",
            default_priority=JobPriority.NORMAL,
            default_retry=RetryPolicy(max_attempts=2),
        )
    )
    return manager


# -- queue ------------------------------------------------------------------


def test_queue_orders_by_priority_then_fifo():
    queue = JobQueue()
    low = Job(id="j1", tenant_id="t", organization_id="t", definition_key="k", priority=JobPriority.LOW)
    high = Job(id="j2", tenant_id="t", organization_id="t", definition_key="k", priority=JobPriority.HIGH)
    normal = Job(id="j3", tenant_id="t", organization_id="t", definition_key="k", priority=JobPriority.NORMAL)
    queue.enqueue(low)
    queue.enqueue(high)
    queue.enqueue(normal)
    assert queue.dequeue() == "j2"  # HIGH first
    assert queue.dequeue() == "j3"  # NORMAL next
    assert queue.dequeue() == "j1"  # LOW last


def test_queue_overflow_raises():
    queue = JobQueue(capacity=1)
    queue.enqueue(Job(id="j1", tenant_id="t", organization_id="t", definition_key="k"))
    with pytest.raises(QueueOverflowError):
        queue.enqueue(Job(id="j2", tenant_id="t", organization_id="t", definition_key="k"))


def test_queue_dequeue_is_tenant_scoped():
    queue = JobQueue()
    queue.enqueue(Job(id="a", tenant_id="t1", organization_id="t1", definition_key="k"))
    queue.enqueue(Job(id="b", tenant_id="t2", organization_id="t2", definition_key="k"))
    assert queue.dequeue(tenant_id="t2") == "b"
    assert queue.size(tenant_id="t1") == 1


# -- scheduler --------------------------------------------------------------


def test_scheduler_releases_due_jobs():
    clock = FrozenClock()
    scheduler = JobScheduler(clock=clock)
    scheduler.schedule("j1", clock.now() + timedelta(seconds=60))
    assert scheduler.due() == []
    clock.advance(seconds=61)
    assert scheduler.due() == ["j1"]
    assert len(scheduler) == 0  # dropped once due


# -- manager lifecycle ------------------------------------------------------


def test_submit_enqueues_and_claim_runs():
    manager = _manager()
    job = manager.submit("t1", "o1", "reindex", priority=JobPriority.HIGH)
    assert job.status == JobStatus.QUEUED
    claimed = manager.claim("worker-1", tenant_id="t1")
    assert claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING
    assert claimed.attempts == 1
    done = manager.complete(claimed.id, result={"ok": True})
    assert done.status == JobStatus.SUCCEEDED


def test_dependencies_block_and_unblock():
    manager = _manager()
    parent = manager.submit("t1", "o1", "reindex")
    child = manager.submit("t1", "o1", "reindex", depends_on=[parent.id])
    assert child.status == JobStatus.BLOCKED
    manager.complete(manager.claim("worker-1", tenant_id="t1").id)
    assert manager.get("t1", child.id).status == JobStatus.QUEUED


def test_dependency_failure_fails_dependents():
    manager = _manager()
    parent = manager.submit("t1", "o1", "reindex", retry=RetryPolicy(max_attempts=1))
    child = manager.submit("t1", "o1", "reindex", depends_on=[parent.id])
    claimed = manager.claim("worker-1", tenant_id="t1")
    manager.fail(claimed.id, error="boom")
    assert manager.get("t1", parent.id).status == JobStatus.FAILED
    assert manager.get("t1", child.id).status == JobStatus.FAILED


def test_retry_then_exhaust():
    manager = _manager()  # max_attempts = 2
    manager.submit("t1", "o1", "reindex")
    first = manager.claim("worker-1", tenant_id="t1")
    manager.fail(first.id, error="transient")
    assert manager.get("t1", first.id).status == JobStatus.QUEUED  # requeued
    second = manager.claim("worker-1", tenant_id="t1")
    manager.fail(second.id, error="again")
    assert manager.get("t1", second.id).status == JobStatus.FAILED


def test_cancel_is_safe_on_terminal_jobs():
    manager = _manager()
    job = manager.submit("t1", "o1", "reindex")
    manager.complete(manager.claim("worker-1", tenant_id="t1").id)
    cancelled = manager.cancel("t1", job.id)
    assert cancelled.status == JobStatus.SUCCEEDED  # not flipped to cancelled


def test_cancel_queued_job_removes_it():
    manager = _manager()
    job = manager.submit("t1", "o1", "reindex")
    manager.cancel("t1", job.id)
    assert manager.get("t1", job.id).status == JobStatus.CANCELLED
    assert manager.queue.peek() is None


def test_jobs_are_tenant_isolated():
    manager = _manager()
    job = manager.submit("t1", "o1", "reindex")
    with pytest.raises(TenantIsolationError):
        manager.get("t2", job.id)


def test_submit_with_unknown_dependency_rejected():
    manager = _manager()
    with pytest.raises(RuntimeValidationError):
        manager.submit("t1", "o1", "reindex", depends_on=["nope"])


def test_scheduled_job_promotes_when_due():
    clock = FrozenClock()
    manager = JobManager(clock=clock)
    manager.define(JobDefinition(id="d", key="k", name="K"))
    job = manager.submit("t1", "o1", "k", run_at=clock.now() + timedelta(seconds=30))
    assert job.status == JobStatus.SCHEDULED
    clock.advance(seconds=31)
    manager.promote_scheduled()
    assert manager.get("t1", job.id).status == JobStatus.QUEUED
