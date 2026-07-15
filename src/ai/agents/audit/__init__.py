"""Enterprise Hiring Audit & Explainability Platform (Phase 5 / Milestone 4).

The Hiring Audit Agent reconstructs the complete hiring journey: why the decision
was made, which AI agents participated, which evidence influenced it, which
assumptions were made, which human approvals occurred, and whether executives can
reconstruct the whole journey. It is **not** a logging system, **not** an
observability tool and **not** a legal-opinion engine — it consumes artefacts the
platform already produced (reusing the Hiring Compliance engine, which
transitively reuses the whole chain) plus an optional injected audit archive, and
clearly separates observed facts, inferred insights, AI recommendations and human
decisions. It never fabricates evidence/approvals/history and never rewrites history.

Importing the package auto-registers the :class:`HiringAuditAgent` with the AI
Platform, the deterministic composer registry and the Multi-Agent Orchestration
registry (side effects in :mod:`agent`).
"""

from __future__ import annotations

from src.ai.agents.audit.agent import (
    AuditInput,
    HiringAuditAgent,
    build_audit_evidence,
    hiring_audit_agent,
)
from src.ai.agents.audit.audit_engine import (
    AuditArchiveProvider,
    HiringAuditEngine,
    NullAuditArchiveProvider,
    hiring_audit_engine,
)
from src.ai.agents.audit.schemas import AuditNarrative, HiringAuditReport

__all__ = [
    "HiringAuditAgent",
    "AuditInput",
    "build_audit_evidence",
    "hiring_audit_agent",
    "HiringAuditEngine",
    "AuditArchiveProvider",
    "NullAuditArchiveProvider",
    "hiring_audit_engine",
    "AuditNarrative",
    "HiringAuditReport",
]
