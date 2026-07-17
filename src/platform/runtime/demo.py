"""Offline demo fixture for the Runtime Operations workspace (Module 10).

Builds a fully-wired :class:`RuntimePlatform` and drives a deterministic
scenario — register job definitions and workers, submit and process jobs
(some succeed, one fails, one is scheduled, one is cancelled), warm the cache,
run a few executions and tick the background services — so the runtime dashboard
and its AppTest render instantly with real-looking data and no network. A
:class:`FrozenClock` makes everything reproducible.
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.platform.common.clock import FrozenClock
from src.platform.runtime.bootstrap import RuntimePlatform, build_runtime_platform
from src.platform.runtime.execution.models import Task
from src.platform.runtime.jobs.models import JobDefinition, JobPriority
from src.platform.runtime.resilience.policies import RetryPolicy

_TENANT = "org_acme"
_ORG = "org_acme"

_DEFINITIONS = [
    ("reindex_candidates", "Reindex Candidates", JobPriority.HIGH),
    ("export_report", "Export Report", JobPriority.NORMAL),
    ("cleanup_temp", "Cleanup Temp Files", JobPriority.LOW),
    ("sync_ats", "Sync ATS", JobPriority.CRITICAL),
]


def build_runtime_demo() -> RuntimePlatform:
    """Return a :class:`RuntimePlatform` driven through a deterministic scenario."""
    clock = FrozenClock()
    rt = build_runtime_platform(clock=clock)

    for key, name, priority in _DEFINITIONS:
        rt.jobs.define(
            JobDefinition(
                id=f"def_{key}",
                key=key,
                name=name,
                default_priority=priority,
                default_retry=RetryPolicy(max_attempts=2),
            )
        )

    # A small worker fleet.
    workers = [rt.workers.register(name=f"worker-{i}") for i in range(3)]

    # Submit a spread of jobs.
    j_reindex = rt.jobs.submit(_TENANT, _ORG, "reindex_candidates", payload={"n": 5000})
    j_export = rt.jobs.submit(_TENANT, _ORG, "export_report")
    j_sync = rt.jobs.submit(_TENANT, _ORG, "sync_ats")
    j_cleanup = rt.jobs.submit(_TENANT, _ORG, "cleanup_temp")

    # Process a couple to completion.
    for worker in workers[:2]:
        claimed = rt.jobs.claim(worker.id, tenant_id=_TENANT)
        if claimed is None:
            continue
        rt.workers.mark_busy(worker.id, claimed.id)
        rt.jobs.complete(claimed.id, result={"ok": True})
        rt.workers.mark_idle(worker.id)

    # One job fails then exhausts retries.
    failing = rt.jobs.claim(workers[2].id, tenant_id=_TENANT)
    if failing is not None:
        rt.jobs.fail(failing.id, error="simulated transient error")
        again = rt.jobs.claim(workers[2].id, tenant_id=_TENANT)
        if again is not None:
            rt.jobs.fail(again.id, error="simulated permanent error")

    # A scheduled job (due in the future) and a cancelled job.
    rt.jobs.submit(
        _TENANT,
        _ORG,
        "export_report",
        run_at=datetime(2027, 1, 1, tzinfo=UTC),
    )
    rt.jobs.cancel(_TENANT, j_cleanup.id)

    # Warm the cache and run a few executions for dashboard metrics.
    rt.cache.analytics_cache.set("kpi:jobs", 42, ttl_seconds=300)
    rt.cache.analytics_cache.get("kpi:jobs")  # a hit
    rt.cache.analytics_cache.get("kpi:missing")  # a miss
    rt.execution.run_sequential([Task("warm_a", lambda: 1), Task("warm_b", lambda: 2)])

    # Tick background maintenance once.
    rt.services.tick()

    return rt
