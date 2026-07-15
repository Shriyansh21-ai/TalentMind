"""Enterprise Hiring Compliance Intelligence System (Phase 5 / Milestone 3).

The Hiring Compliance Agent evaluates whether a hiring workflow follows company
governance: required approvals, mandatory steps, internal-policy compliance,
documentation presence, audit-trail readiness and governance risk. It is **not** a
legal-advice system and **not** a law engine — it consumes existing intelligence
(reusing the Pay Equity Guardian, which transitively reuses Compensation
Governance + the committee) plus optional injected governance data, and surfaces
governance risks and human-review needs only. It gives no legal advice and
fabricates no compliance conclusion.

Importing the package auto-registers the :class:`HiringComplianceAgent` with the
AI Platform, the deterministic composer registry and the Multi-Agent Orchestration
registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.compliance.agent import (
    ComplianceInput,
    HiringComplianceAgent,
    build_compliance_evidence,
    compliance_agent,
)
from src.ai.agents.compliance.compliance_report import (
    ComplianceDataProvider,
    HiringComplianceEngine,
    NullComplianceDataProvider,
    hiring_compliance_engine,
)
from src.ai.agents.compliance.schemas import (
    ComplianceNarrative,
    HiringComplianceReport,
)

__all__ = [
    "HiringComplianceAgent",
    "ComplianceInput",
    "build_compliance_evidence",
    "compliance_agent",
    "HiringComplianceEngine",
    "ComplianceDataProvider",
    "NullComplianceDataProvider",
    "hiring_compliance_engine",
    "ComplianceNarrative",
    "HiringComplianceReport",
]
