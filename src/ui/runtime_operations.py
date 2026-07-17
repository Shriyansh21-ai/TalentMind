"""Runtime Operations workspace (Phase 6 / Milestone 3 — Module 10).

An enterprise runtime operations console: platform health, worker fleet, queues
and jobs (running / completed / failed), cache, performance, runtime metrics,
resource utilization and circuit breakers.

The page is UI-only and fully offline. It drives a deterministic, pre-seeded
demo runtime (:func:`build_runtime_demo`), so it renders instantly with no
dataset, provider or network — and the AppTest stays fast. All logic lives in
``src/platform/runtime``; this module only presents it.
"""

from __future__ import annotations

import streamlit as st

from src.platform.runtime.demo import build_runtime_demo
from src.platform.runtime.jobs.models import JobStatus

_RUNTIME_KEY = "runtime_ops_instance"
_TENANT = "org_acme"


def _get_runtime():
    """Return the pre-seeded demo runtime, cached for the session."""
    if _RUNTIME_KEY not in st.session_state:
        st.session_state[_RUNTIME_KEY] = build_runtime_demo()
    return st.session_state[_RUNTIME_KEY]


def render_runtime_operations() -> None:
    """Render the Runtime Operations workspace."""
    st.title("⚙️ Runtime Operations")
    st.caption(
        "Enterprise runtime console — background jobs, workers, queues, cache, "
        "health, resilience, load management and resource utilization for the "
        "TalentMind production runtime. Offline by default."
    )

    rt = _get_runtime()
    _render_kpis(rt)

    (
        tab_health,
        tab_workers,
        tab_jobs,
        tab_cache,
        tab_perf,
        tab_resources,
        tab_circuit,
        tab_events,
    ) = st.tabs(
        [
            "❤️ Health",
            "👷 Workers",
            "📥 Queues & Jobs",
            "🗃️ Cache",
            "🚀 Performance",
            "📊 Resources",
            "🔌 Circuit Breakers",
            "📡 Runtime Events",
        ]
    )

    with tab_health:
        _render_health(rt)
    with tab_workers:
        _render_workers(rt)
    with tab_jobs:
        _render_jobs(rt)
    with tab_cache:
        _render_cache(rt)
    with tab_perf:
        _render_performance(rt)
    with tab_resources:
        _render_resources(rt)
    with tab_circuit:
        _render_circuit(rt)
    with tab_events:
        _render_events(rt)


# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------


def _render_kpis(rt) -> None:
    """Render top-line runtime KPIs."""
    stats = rt.jobs.stats(_TENANT)
    wm = rt.workers.metrics()
    cache_stats = rt.cache.stats()

    cols = st.columns(6)
    cols[0].metric("Workers", wm["active"])
    cols[1].metric("Queue depth", len(rt.jobs.queue))
    cols[2].metric("Running", stats.get("running", 0))
    cols[3].metric("Succeeded", stats.get("succeeded", 0))
    cols[4].metric("Failed", stats.get("failed", 0))
    hit = getattr(rt.cache.provider, "hit_rate", 0.0)
    cols[5].metric("Cache hit rate", f"{hit * 100:.0f}%")


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


def _render_health(rt) -> None:
    """Render platform + component health."""
    st.subheader("Platform Health")
    report = rt.health.check()
    banner = {
        "healthy": st.success,
        "degraded": st.warning,
        "unhealthy": st.error,
        "unknown": st.info,
    }.get(report.state.value, st.info)
    banner(f"Overall runtime health: {report.state.value.upper()}")

    rows = [
        {
            "component": c.name,
            "state": c.state.value,
            "message": c.message,
            "details": ", ".join(f"{k}={v}" for k, v in list(c.details.items())[:4]),
        }
        for c in report.components
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_workers(rt) -> None:
    """Render the worker fleet and aggregate metrics."""
    st.subheader("Workers")
    metrics = rt.workers.metrics()
    cols = st.columns(5)
    cols[0].metric("Total", metrics["total"])
    cols[1].metric("Idle", metrics["idle"])
    cols[2].metric("Busy", metrics["busy"])
    cols[3].metric("Unhealthy", metrics["unhealthy"])
    cols[4].metric("Jobs processed", metrics["jobs_processed"])

    rows = [
        {
            "worker": w.name,
            "status": w.status.value,
            "current_job": w.current_job_id or "—",
            "processed": w.metrics.jobs_processed,
            "failed": w.metrics.jobs_failed,
            "heartbeats": w.metrics.heartbeats,
        }
        for w in rt.workers.workers()
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_jobs(rt) -> None:
    """Render queue depth and jobs grouped by lifecycle state."""
    st.subheader("Queue")
    st.caption(
        f"Depth {len(rt.jobs.queue)} / capacity {rt.jobs.queue.capacity} · "
        f"by priority: {rt.jobs.queue.depth_by_priority()}"
    )

    st.subheader("Jobs")
    rows = [
        {
            "job": j.name,
            "definition": j.definition_key,
            "status": j.status.value,
            "priority": j.priority.name,
            "attempts": j.attempts,
            "depends_on": len(j.depends_on),
        }
        for j in rt.jobs.list(_TENANT)
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    for label, status in [
        ("Running Jobs", JobStatus.RUNNING),
        ("Completed Jobs", JobStatus.SUCCEEDED),
        ("Failed Jobs", JobStatus.FAILED),
    ]:
        jobs = rt.jobs.list(_TENANT, status=status)
        st.markdown(f"**{label}** — {len(jobs)}")


def _render_cache(rt) -> None:
    """Render cache statistics."""
    st.subheader("Cache")
    stats = rt.cache.stats()
    cols = st.columns(4)
    cols[0].metric("Entries", stats.get("size", 0))
    cols[1].metric("Hits", stats.get("hits", 0))
    cols[2].metric("Misses", stats.get("misses", 0))
    hit = getattr(rt.cache.provider, "hit_rate", 0.0)
    cols[3].metric("Hit rate", f"{hit * 100:.0f}%")
    st.caption(
        f"Namespaces: tenant · session · config · analytics · provider = {rt.cache.provider.name}"
    )


def _render_performance(rt) -> None:
    """Render execution/latency telemetry."""
    st.subheader("Performance")
    latency_rows = [
        {
            "metric": s.name,
            "count": s.count,
            "avg_ms": round(s.avg_ms, 2),
            "max_ms": round(s.max_ms, 2),
        }
        for s in rt.telemetry.latency()
    ]
    if latency_rows:
        st.markdown("#### Latency")
        st.dataframe(latency_rows, use_container_width=True, hide_index=True)

    exec_rows = [
        {
            "surface": c.name,
            "executions": c.executions,
            "failures": c.failures,
            "success_rate": f"{c.success_rate * 100:.0f}%",
        }
        for c in rt.telemetry.executions()
    ]
    if exec_rows:
        st.markdown("#### Executions")
        st.dataframe(exec_rows, use_container_width=True, hide_index=True)
    if not latency_rows and not exec_rows:
        st.info("No performance samples recorded yet.")


def _render_resources(rt) -> None:
    """Render resource utilization and a capacity plan."""
    st.subheader("Resource Utilization")
    util = rt.resources.utilization()
    sys = util.system
    app = util.application
    if sys.available:
        cols = st.columns(3)
        cols[0].metric("CPU %", sys.cpu_percent)
        cols[1].metric("Memory %", sys.memory_percent)
        cols[2].metric("Disk %", sys.disk_percent)
    else:
        st.info("System metrics unavailable offline (psutil not installed).")

    cols = st.columns(4)
    cols[0].metric("Queue depth", app.queue_depth)
    cols[1].metric("Active workers", app.active_workers)
    cols[2].metric("Running jobs", app.running_jobs)
    cols[3].metric("Open connections", app.open_connections)

    plan = rt.resources.plan_capacity()
    st.caption(
        f"Capacity plan — pressure {plan.queue_pressure} · "
        f"recommended workers {plan.recommended_workers} · {plan.rationale}"
    )


def _render_circuit(rt) -> None:
    """Render circuit-breaker and load-management state."""
    st.subheader("Circuit Breakers & Load")
    snapshot = rt.load.snapshot()
    circuit = snapshot["circuit"]
    cols = st.columns(3)
    cols[0].metric("Circuit", circuit["state"])
    cols[1].metric("Concurrency active", snapshot["concurrency"]["active"])
    cols[2].metric("Adaptive limit", snapshot["adaptive_limit"])
    st.json(snapshot)


def _render_events(rt) -> None:
    """Render the runtime event stream (on the shared enterprise event bus)."""
    st.subheader("Runtime Events")
    events = rt.events.history()
    st.caption(f"{len(events)} runtime events on the enterprise event bus")
    rows = [
        {"seq": e.sequence, "topic": e.topic, "type": e.event_type.value}
        for e in sorted(events, key=lambda e: e.sequence, reverse=True)[:100]
    ]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No runtime events published yet.")
