"""Executive review engine (Module 7).

Determines which approvers the offer requires — Recruiter, Hiring Manager, HR,
Finance, Legal, Executive — and the overall review level, with a reason for each.
Legal review is requested only to *examine pay-equity exposure*; it is never a
legal conclusion or a discrimination finding (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict

from src.ai.agents.pay_equity.schemas import (
    ApprovalRequirement,
    CompressionAssessment,
    EquityRisk,
    ExecutiveReview,
    InversionAssessment,
    PolicyAlignment,
)


def build_executive_review(
    context: Dict[str, Any],
    equity_risk: EquityRisk,
    compression: CompressionAssessment,
    inversion: InversionAssessment,
    policy_alignment: PolicyAlignment,
) -> ExecutiveReview:
    """Determine the required approvals + review level for the offer (Module 7)."""
    hire_type = str(context.get("hire_type", ""))
    market_position = str(context.get("market_position", ""))
    outside_band = bool(context.get("outside_band"))
    high_risk = equity_risk.level == "High"
    medium_risk = equity_risk.level == "Medium"

    approvals = [
        ApprovalRequirement("Recruiter", True, "Owns the offer and the candidate relationship."),
        ApprovalRequirement("Hiring Manager", True, "Owns the role, level and team fit."),
        ApprovalRequirement("HR", True, "Owns compensation policy and internal equity."),
    ]

    finance_needed = outside_band or market_position in ("Premium", "Strategic Premium") or hire_type == "Critical Hire"
    approvals.append(
        ApprovalRequirement(
            "Finance",
            finance_needed,
            "Budget impact of an above-band / premium / critical offer." if finance_needed
            else "Within budget norms; no separate finance sign-off required.",
        )
    )

    legal_needed = inversion.risk_level in ("Medium", "High") or compression.risk_level == "High"
    approvals.append(
        ApprovalRequirement(
            "Legal",
            legal_needed,
            "Review pay-equity exposure from detected inversion/compression (governance review, not a legal finding)."
            if legal_needed else "No pay-equity exposure flagged for legal review.",
        )
    )

    exec_needed = high_risk or policy_alignment.alignment == "Violation" or hire_type == "Critical Hire"
    approvals.append(
        ApprovalRequirement(
            "Executive",
            exec_needed,
            "High equity risk / policy exception / critical hire warrants executive sponsorship."
            if exec_needed else "No executive sponsorship required.",
        )
    )

    if exec_needed:
        review_level = "Executive"
    elif finance_needed or legal_needed or medium_risk:
        review_level = "Elevated"
    else:
        review_level = "Standard"

    required = [a.approver for a in approvals if a.required]
    rationale = (
        f"Review level '{review_level}'. Required approvers: {', '.join(required)}. "
        + (f"Driven by: {'; '.join(equity_risk.drivers[:2])}" if equity_risk.data_available else
           "Internal data unavailable; baseline governance approvals apply.")
    )

    return ExecutiveReview(review_level=review_level, approvals=approvals, rationale=rationale)
