"""TalentMind Enterprise Integration Platform (Phase 6 / Milestone 2).

Turns the Enterprise SaaS foundation (Milestone 1) into an *integration-ready*
platform that can connect to the ecosystem used by Fortune 500 companies —
HRIS, ATS, calendars, communication, document stores — through a uniform,
swappable provider model, an API gateway, a webhook platform, an event bus and a
synchronization framework.

Everything here is **additive** and **offline by default**. No real integration
is implemented: every provider is an interface, every connection is simulated,
and no network call is ever made. The platform never imports or modifies the
Phase 1-5 hiring/scoring/semantic/intelligence engines — it only provides the
architecture a future production integration binds to.

Modules
-------
``common``         Module 1  — integration models, provider seam, registry, secrets.
``manager``        Module 1  — integration lifecycle control plane.
``hris``           Module 2  — HRIS provider interfaces.
``ats``            Module 3  — ATS provider interfaces.
``calendar``       Module 4  — scheduling / availability / slots + providers.
``communication``  Module 5  — channels / templates + providers.
``documents``      Module 6  — document metadata / versioning + providers.
``gateway``        Module 7  — enterprise API gateway.
``webhooks``       Module 8  — signed webhook platform.
``sync``           Module 9  — synchronization framework.
``events``         Module 10 — enterprise event bus.
``marketplace``    Module 11 — integration marketplace (read-side aggregation).
``sdk``            Module 12 — developer SDK foundation.
``observability``  Module 15 — integration telemetry.
``bootstrap``      Module 14 — lazy DI composition root.
"""

from __future__ import annotations

from src.platform.integrations.bootstrap import (
    IntegrationPlatform,
    build_integration_platform,
)
from src.platform.integrations.common import (
    BaseIntegrationProvider,
    Integration,
    IntegrationCapabilities,
    IntegrationConfiguration,
    IntegrationDefinition,
    IntegrationHealth,
    IntegrationMetadata,
    IntegrationProvider,
    IntegrationRegistry,
    IntegrationStatus,
    ProviderCategory,
    build_default_registry,
)
from src.platform.integrations.manager import IntegrationManager

__all__ = [
    "IntegrationPlatform",
    "build_integration_platform",
    "IntegrationManager",
    "IntegrationRegistry",
    "build_default_registry",
    "IntegrationProvider",
    "BaseIntegrationProvider",
    "IntegrationDefinition",
    "IntegrationConfiguration",
    "IntegrationMetadata",
    "IntegrationCapabilities",
    "IntegrationHealth",
    "IntegrationStatus",
    "Integration",
    "ProviderCategory",
]

__version__ = "6.2.0"
