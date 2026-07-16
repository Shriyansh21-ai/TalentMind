"""TalentMind Enterprise Runtime Platform (Phase 6 / Milestone 3).

Turns TalentMind into a production-scale platform capable of serving thousands
of concurrent users. This package adds the *runtime infrastructure* — background
jobs, workers, a task-execution engine, a distributed cache layer, health
monitoring, load management, resilience, resource management, runtime events and
observability — that every subsystem can reuse.

Everything here is **additive**, **offline by default** and **independent of
hiring logic**. It never imports or modifies the Phase 1-5
hiring/scoring/semantic/intelligence engines; it provides no new AI agents and
changes no business logic. It is deterministic and clock-driven (no wall-clock
sleeps, no threads spun implicitly), and horizontally scalable by design — ready
for future deployment on Docker, Kubernetes and cloud-native infrastructure.

Modules
-------
``jobs``          Module 1  — background job platform (registry/queue/scheduler/manager).
``workers``       Module 2  — worker framework (pool/lifecycle/health/scaling).
``execution``     Module 3  — task execution engine (sequential/parallel/batch/chunk).
``cache``         Module 4  — distributed cache layer (providers/manager/namespaces).
``performance``   Module 5  — performance optimization framework.
``health``        Module 6  — health monitoring & aggregation.
``load``          Module 7  — load management (concurrency/backpressure/circuit/bulkhead).
``resilience``    Module 8  — resilience framework (retry/fallback/timeout/circuit).
``resources``     Module 9  — resource management & capacity planning.
``services``      Module 11 — background/maintenance services.
``events``        Module 12 — runtime events (over the M2 event bus).
``observability`` Module 13 — runtime logs/metrics + OpenTelemetry-ready tracing.
``bootstrap``     Module 14 — lazy DI composition root.
"""

from __future__ import annotations

from src.platform.runtime.bootstrap import RuntimePlatform, build_runtime_platform

__all__ = ["RuntimePlatform", "build_runtime_platform", "__version__"]

__version__ = "6.3.0"
