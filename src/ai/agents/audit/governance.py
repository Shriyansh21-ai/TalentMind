"""Audit readiness + report scaffolding (Modules 7, 9).

Owns the Module 7 audit-readiness assessment (audit status, missing evidence /
documents / approvals, unverified decisions, governance completeness, readiness
level) and the ordered section registry for the Module 9 executive audit report.
Everything is derived from the reused compliance/governance signals; nothing is
fabricated (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.ai.agents.audit.schemas import AuditReadiness
from src.ai.agents.audit.templates import AGENT_CATALOG

# Ordered sections of the executive audit report (Module 9).
REPORT_SECTIONS: List[Tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("decision_journey", "Decision Journey"),
    ("evidence_graph", "Evidence Graph"),
    ("approval_chain", "Approval Chain"),
    ("human_decisions", "Human Decisions"),
    ("ai_decisions", "AI Decisions"),
    ("governance_review", "Governance Review"),
    ("outstanding_risks", "Outstanding Risks"),
    ("audit_recommendations", "Audit Recommendations"),
]


def section_titles() -> List[str]:
    """Return the ordered audit-report section titles."""
    return [title for _key, title in REPORT_SECTIONS]


def build_audit_readiness(context: Dict[str, Any]) -> AuditReadiness:
    """Assess audit readiness (Module 7)."""
    sources = set(context.get("evidence_sources", []))
    workflow = context.get("workflow", {}) or {}
    approvals = context.get("approvals", {}) or {}
    documentation = context.get("documentation", {}) or {}
    audit = context.get("audit", {}) or {}
    data_available = bool(context.get("data_available"))

    # Missing evidence = catalog agents that did not participate.
    missing_evidence = [e.stage for e in AGENT_CATALOG if e.source not in sources]
    missing_documents = list(documentation.get("missing", []))
    missing_approvals = list(approvals.get("outstanding", []))

    # Unverified decisions = audit dimensions not Complete + pending approvals.
    unverified = [f["dimension"] for f in audit.get("findings", []) if f.get("status") != "Complete"]
    if missing_approvals:
        unverified.append(f"Approvals: {', '.join(missing_approvals)}")

    completeness = (
        f"Workflow {workflow.get('status', 'Requires Review')} "
        f"({workflow.get('completed', 0)}/{workflow.get('total', 0)}); audit {audit.get('status', 'Needs Investigation')}."
    )

    # Readiness level: penalize missing evidence + unverified decisions + no data.
    if not data_available:
        level, status = "Medium", "Partially Ready"
    elif not missing_evidence and not missing_approvals and audit.get("status") == "Complete":
        level, status = "High", "Ready"
    elif len(missing_evidence) >= 4:
        level, status = "Low", "Not Ready"
    else:
        level, status = "Medium", "Partially Ready"

    return AuditReadiness(
        status=status,
        readiness_level=level,
        governance_completeness=completeness,
        missing_evidence=missing_evidence,
        missing_documents=missing_documents,
        missing_approvals=missing_approvals,
        unverified_decisions=list(dict.fromkeys(unverified)),
    )
