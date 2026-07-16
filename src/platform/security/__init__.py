"""TalentMind Enterprise Security, Governance & Observability Platform
(Phase 6 / Milestone 4).

Makes TalentMind operationally trustworthy for enterprise deployment: identity,
authorization (RBAC + ABAC), a central audit platform, secret management,
unified observability, monitoring, governance, compliance, threat detection,
configuration governance, incident management and operational analytics.

Everything here is **additive**, **deterministic** and **offline by default**.
It introduces no external identity providers, makes no network calls, and never
imports or modifies the Phase 1-5 hiring/scoring/semantic/intelligence engines
or any prior-milestone business logic. It is architecturally ready for Azure,
AWS, GCP, Okta, Auth0, SAML, OIDC, Vault, OpenTelemetry, Prometheus and Grafana
without requiring architectural redesign.

Modules
-------
``identity``       Module 1  — enterprise identity framework (local + future IdPs).
``authorization``  Module 2  — RBAC hierarchies + ABAC policy engine.
``audit``          Module 3  — central hash-chained audit platform.
``secrets``        Module 4  — secret manager + cloud provider interfaces.
``observability``  Module 5  — unified logs/metrics/traces (OTel-ready).
``monitoring``     Module 6  — alert rules + notification hooks.
``governance``     Module 7  — policy registry, evaluation, exceptions.
``compliance``     Module 8  — GDPR/SOC2/ISO27001/HIPAA/PCI-DSS frameworks.
``threat``         Module 9  — threat detection + SIEM interface.
``configuration``  Module 11 — versioned configuration governance.
``incidents``      Module 12 — incident management.
``analytics``      Module 13 — operational analytics.
``bootstrap``      Module 14 — lazy DI composition root.
"""

from __future__ import annotations

from src.platform.security.bootstrap import (
    SecurityPlatform,
    build_security_platform,
)

__all__ = ["SecurityPlatform", "build_security_platform", "__version__"]

__version__ = "6.4.0"
