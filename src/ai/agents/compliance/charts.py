"""Visualization data for the Compliance dashboard (Module 10).

Pure data builders (no plotting, no Streamlit import): a compliance-status view,
the approval flow, workflow completion, audit readiness, governance health,
missing documentation and the executive approval matrix. Every value is a
qualitative status or a coverage count — never a fabricated compliance figure.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import (
    ApprovalMatrix,
    AuditTrailValidation,
    DocumentationReview,
    GovernanceRisk,
    WorkflowCompliance,
)

_RISK_INDEX = {"low": 1, "medium": 2, "high": 3}
_AUDIT_INDEX = {"complete": 3, "incomplete": 2, "needs investigation": 1}


def build_chart_data(
    *,
    workflow: WorkflowCompliance,
    approvals: ApprovalMatrix,
    documentation: DocumentationReview,
    audit: AuditTrailValidation,
    governance_risk: GovernanceRisk,
) -> dict[str, Any]:
    """Build every chart structure for the compliance dashboard (Module 10)."""
    return {
        "compliance_status": {
            "workflow_status": workflow.status,
            "governance_risk": governance_risk.level,
            "audit_status": audit.status,
        },
        "workflow_completion": {
            "completed": workflow.completed,
            "total": workflow.total,
            "ratio": round(workflow.completed / workflow.total, 3) if workflow.total else 0.0,
            "steps": {s.name: s.status for s in workflow.steps},
        },
        "approval_flow": [
            {"approver": a.approver, "required": a.required, "state": a.state}
            for a in approvals.approvals
        ],
        "executive_approval_matrix": {
            a.approver: a.state for a in approvals.approvals if a.required
        },
        "audit_readiness": {
            "status": audit.status,
            "index": _AUDIT_INDEX.get(audit.status.lower(), 1),
            "findings": {f.dimension: f.status for f in audit.findings},
        },
        "governance_health": {
            "level": governance_risk.level,
            "index": _RISK_INDEX.get(governance_risk.level.lower(), 2),
            "scale": ["Low", "Medium", "High"],
            "missing_controls": len(governance_risk.missing_controls),
        },
        "missing_documentation": list(documentation.missing()),
    }
