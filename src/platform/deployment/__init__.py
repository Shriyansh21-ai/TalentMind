"""TalentMind Enterprise Deployment Platform (Phase 6 / Milestone 5).

Makes TalentMind deployable, maintainable, scalable and enterprise-ready. This
package adds the production-engineering layer: a deployment manager (profiles,
targets, plans, rollback, health), a configuration platform, a backup & recovery
framework, release engineering (semantic versioning, manifests, notes,
compatibility, migrations, deprecations), a production validator and a
performance benchmark framework.

Everything is **additive**, **deterministic** and **offline by default**. It
adds no hiring functionality, no AI agents, and no changes to existing
architecture — it *plans, validates, versions and measures* the platform that
already exists. Container, Kubernetes and CI/CD artifacts live at the repository
root (``Dockerfile``, ``docker-compose*.yml``, ``k8s/``, ``.github/workflows/``).

Modules
-------
``manager``        Module 1 — deployment manager, profiles, plans, rollback, health.
``environment``    Module 1 — deterministic environment detection.
``configuration``  Module 5 — environment configuration profiles + loader/export.
``backup``         Module 6 — backup & recovery framework (interfaces only).
``release``        Module 7 — semantic versioning + release engineering.
``validation``     Module 8 — production readiness validator + report.
``benchmark``      Module 9 — performance benchmark framework (real timing).
``bootstrap``      Module 15 — lazy DI composition root.
"""

from __future__ import annotations

from src.platform.deployment.bootstrap import (
    DeploymentPlatform,
    build_deployment_platform,
)
from src.platform.deployment.packaging import (
    InstallationReport,
    PackageInfo,
    offline_install_notes,
    package_info,
    verify_installation,
)

__all__ = [
    "DeploymentPlatform",
    "build_deployment_platform",
    "PackageInfo",
    "InstallationReport",
    "package_info",
    "verify_installation",
    "offline_install_notes",
    "__version__",
]

__version__ = "1.0.0"
