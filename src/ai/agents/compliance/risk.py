"""Governance risk assessment (Module 5).

Rolls the workflow, exceptions and policy findings into an overall governance
risk (Low / Medium / High) with the driving evidence, the missing controls and
the human-review recommendations. It surfaces organizational governance risk —
never a legal risk ruling (Module 14).
"""

from __future__ import annotations

from src.ai.agents.compliance.schemas import (
    ApprovalMatrix,
    ComplianceException,
    DocumentationReview,
    GovernanceRisk,
    WorkflowCompliance,
)


def assess_governance_risk(
    workflow: WorkflowCompliance,
    exceptions: list[ComplianceException],
    approvals: ApprovalMatrix,
    documentation: DocumentationReview,
) -> GovernanceRisk:
    """Assess overall governance risk (Module 5)."""
    real_exceptions = [e for e in exceptions if e.kind != "No exceptions detected"]
    high = [e for e in real_exceptions if e.severity == "High"]
    medium = [e for e in real_exceptions if e.severity == "Medium"]

    missing_controls: list[str] = []
    missing_controls += [s.name for s in workflow.steps if s.status == "Missing" and s.critical]
    missing_controls += [f"{a} approval" for a in approvals.outstanding()]
    missing_controls += documentation.missing()

    if high:
        level = "High"
    elif medium or missing_controls:
        level = "Medium"
    else:
        level = "Low"

    drivers = [e.kind for e in real_exceptions[:5]] or ["No governance exceptions detected."]
    human_review = list(
        dict.fromkeys(e.recommendation for e in (high + medium) if e.recommendation)
    )[:5]
    if not human_review:
        human_review = ["Proceed through standard approvals; no elevated review indicated."]

    confidence = 60.0 + (10.0 if workflow.total else 0.0) + (10.0 if real_exceptions else 0.0)

    return GovernanceRisk(
        level=level,
        drivers=drivers,
        missing_controls=list(dict.fromkeys(missing_controls)),
        human_review_recommendations=human_review,
        confidence=round(min(100.0, confidence), 1),
    )
