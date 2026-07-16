"""TalentMind Enterprise SaaS Platform Foundation (Phase 6 / Milestone 1).

This package turns TalentMind from a single-tenant hiring application into a
true multi-tenant Enterprise SaaS platform capable of securely hosting thousands
of organizations.

Everything in :mod:`src.platform` is **additive**. It introduces no dependency
on and makes no modification to the Phase 1-5 hiring, scoring, semantic or
intelligence engines. Those engines continue to run unchanged; the platform
simply provides the enterprise scaffolding (organizations, tenants, identity,
access control, workspaces, configuration, subscriptions, notifications,
auditing, API contracts, storage abstractions and a developer platform) that a
future integration layer can bind them to.

Design principles
-----------------
* **Additive only** — never import from or mutate existing business logic.
* **Offline & dependency-light** — stdlib + pydantic only; no network, no keys.
* **SOLID / Clean Architecture** — models, repositories and services are
  separated; interfaces (protocols/ABCs) are defined before implementations.
* **Multi-tenant by construction** — tenant scoping is enforced at the
  repository layer so cross-tenant leakage is structurally impossible.

Sub-packages
------------
``common``         Shared base models, errors, ids, clock and the repository pattern.
``organizations`` Module 1  — organization/business-unit/department/office tree.
``tenancy``       Module 2  — tenant context, resolver, isolation, cache, storage.
``auth``          Module 3  — authentication architecture (no OAuth yet).
``rbac``          Module 4  — enterprise role-based access control.
``workspaces``    Module 5  — organization-owned workspaces and resources.
``config``        Module 6  — feature flags, licensing, localization, limits.
``subscription``  Module 7  — plan/seat/usage/credit architecture (no billing).
``notifications`` Module 8  — reusable notification framework (interfaces only).
``audit``         Module 9  — platform-level audit framework.
``api``           Module 10 — REST contracts: versioning, pagination, errors.
``storage``       Module 11 — storage provider abstractions (interfaces only).
``developer``     Module 12 — plugin/hook/event/SDK framework.
``container``     Module 14 — lazy dependency-injection container.
``integrations``  Phase 6 / Milestone 2 — Enterprise Integration Platform
                  (HRIS/ATS/calendar/communication/document providers, API
                  gateway, webhooks, event bus, synchronization, marketplace and
                  developer SDK foundation — additive, offline, interfaces only).
``runtime``       Phase 6 / Milestone 3 — Enterprise Runtime Platform
                  (background jobs, workers, task execution, distributed cache,
                  health, load management, resilience, resources, runtime events
                  and observability — additive, offline, horizontally scalable).
``security``      Phase 6 / Milestone 4 — Enterprise Security, Governance &
                  Observability Platform (identity, RBAC+ABAC, central audit,
                  secrets, observability, monitoring, governance, compliance,
                  threat detection, configuration governance, incidents and
                  operational analytics — additive, deterministic, offline).
``deployment``    Phase 6 / Milestone 5 — Enterprise Deployment Platform
                  (deployment manager, configuration, backup/recovery, release
                  engineering, production validation, benchmarking, packaging
                  and repository health — additive, deterministic, offline).
                  Ships TalentMind as Version 1.0.0 Enterprise Edition.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "6.5.0"
