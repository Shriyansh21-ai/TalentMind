"""Composition, architecture & end-to-end tests for the Runtime Platform.

Verifies the runtime composition root wires every module as lazy singletons,
that the whole ``src/platform/runtime`` tree is strictly **additive** (never
imports Phase 1-5 business logic), that it is reachable from the main platform
facade and shares the integration event bus, and that a submit→claim→complete
flow plus background services and observability work end-to-end.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.platform.bootstrap import build_platform
from src.platform.common.clock import FrozenClock
from src.platform.runtime import build_runtime_platform
from src.platform.runtime.demo import build_runtime_demo
from src.platform.runtime.jobs.models import JobDefinition, JobStatus

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "src" / "platform" / "runtime"

_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(from|import)\s+src\."
    r"(scoring|semantic|intelligence|hiring|recruiter|pipeline|reasoning|"
    r"ingestion|insights|comparison|talent_pool|interview|filtering|dashboard|"
    r"llm|ai|models)\b",
    re.MULTILINE,
)


# -- architecture -----------------------------------------------------------


def test_runtime_never_imports_business_logic():
    offenders: list[str] = []
    for path in RUNTIME_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_IMPORT.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"runtime imported business logic: {offenders}"


def test_every_runtime_subpackage_imports():
    import importlib

    for name in [
        "common",
        "jobs",
        "workers",
        "execution",
        "cache",
        "performance",
        "health",
        "load",
        "resilience",
        "resources",
        "services",
        "events",
        "observability",
    ]:
        importlib.import_module(f"src.platform.runtime.{name}")


def test_app_exposes_runtime_operations_nav():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Runtime Operations" in app_src
    assert "_render_runtime_operations_workspace" in app_src


# -- composition root -------------------------------------------------------


def test_build_runtime_platform_wires_all_services():
    rt = build_runtime_platform(clock=FrozenClock())
    for key in [
        "runtime.telemetry",
        "runtime.events",
        "runtime.jobs",
        "runtime.workers",
        "runtime.execution",
        "runtime.cache",
        "runtime.resilience",
        "runtime.load",
        "runtime.resources",
        "runtime.health",
        "runtime.services",
    ]:
        assert rt.container.has(key)
    assert rt.jobs is rt.jobs  # lazy singleton


def test_runtime_reachable_from_main_platform_and_shares_bus():
    main = build_platform(clock=FrozenClock())
    # Runtime events publish onto the integration platform's enterprise bus.
    assert main.runtime.events.bus is main.integrations.events
    main.runtime.jobs.define(JobDefinition(id="d", key="k", name="K"))
    main.runtime.jobs.submit("t1", "o1", "k")
    assert any(e.topic.startswith("runtime.") for e in main.integrations.events.history())


def test_two_runtime_platforms_are_independent():
    a = build_runtime_platform(clock=FrozenClock())
    b = build_runtime_platform(clock=FrozenClock())
    a.jobs.define(JobDefinition(id="d", key="k", name="K"))
    a.jobs.submit("t1", "o1", "k")
    assert len(a.jobs.list("t1")) == 1
    assert len(b.jobs.list("t1")) == 0


# -- end-to-end -------------------------------------------------------------


def test_end_to_end_job_flow_with_worker_and_telemetry():
    rt = build_runtime_platform(clock=FrozenClock())
    rt.jobs.define(JobDefinition(id="d", key="reindex", name="Reindex"))
    worker = rt.workers.register(name="w1")
    job = rt.jobs.submit("t1", "o1", "reindex")

    claimed = rt.jobs.claim(worker.id, tenant_id="t1")
    rt.workers.mark_busy(worker.id, claimed.id)
    rt.jobs.complete(claimed.id, result={"ok": True})
    rt.workers.mark_idle(worker.id)

    assert rt.jobs.get("t1", job.id).status == JobStatus.SUCCEEDED
    assert rt.workers.metrics()["jobs_processed"] == 1
    # Telemetry recorded the execution + runtime events fired.
    assert any(c.name == "job:reindex" for c in rt.telemetry.executions())
    assert any(e.topic == "runtime.job.succeeded" for e in rt.events.history())


def test_background_services_tick_runs_maintenance():
    rt = build_runtime_platform(clock=FrozenClock())
    results = rt.services.tick()
    assert "cache_cleanup" in results
    assert "health_polling" in results


def test_demo_runtime_is_seeded():
    rt = build_runtime_demo()
    stats = rt.jobs.stats("org_acme")
    assert stats.get("succeeded", 0) >= 2
    assert stats.get("failed", 0) >= 1
    assert len(rt.workers.workers()) == 3
    assert len(rt.events.history()) > 0
