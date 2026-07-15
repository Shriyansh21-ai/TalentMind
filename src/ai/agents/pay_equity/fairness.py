"""Fairness intelligence (Module 6).

Produces the fairness assessment: potential concerns, human-review
recommendations, governance notes, the observed evidence it rests on and the
explicit assumptions. It identifies **areas requiring review only** — it makes no
legal conclusion and never accuses discrimination (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.pay_equity import governance as governance_mod
from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    ExecutiveReview,
    FairnessAssessment,
    InversionAssessment,
    PolicyAlignment,
    PromotionEquityAssessment,
)


def build_fairness_assessment(
    context: Dict[str, Any],
    compression: CompressionAssessment,
    inversion: InversionAssessment,
    promotion: PromotionEquityAssessment,
    policy_alignment: PolicyAlignment,
    executive_review: ExecutiveReview,
) -> FairnessAssessment:
    """Build the fairness assessment (Module 6)."""
    data_available = compression.data_available or inversion.data_available

    concerns: List[str] = []
    review_recs: List[str] = []
    evidence: List[str] = []
    assumptions: List[str] = []

    if not data_available:
        assessment = (
            "Internal fairness cannot be validated: no company compensation data is "
            "connected. The offer's external-facing rationale (via Compensation "
            "Governance) is available, but internal comparisons are unavailable."
        )
        assumptions.append("No internal payroll/HRIS data available; internal-equity checks are deferred.")
        review_recs.append("Connect an HRIS source, then re-run internal-equity validation.")
    else:
        assessment = (
            "Internal fairness assessed against connected peer data. Findings below "
            "surface governance risks for human review; they are not legal conclusions."
        )
        if compression.risk_level in ("Medium", "High"):
            concerns.append(f"{compression.risk_level} compression risk vs. tenured peers.")
            evidence.extend(compression.evidence[:2])
        if inversion.risk_level in ("Medium", "High"):
            concerns.append(f"{inversion.risk_level} pay-inversion risk vs. equivalent-responsibility peers.")
            review_recs.append(inversion.recommended_review)

    if policy_alignment.alignment in ("Partial", "Violation"):
        concerns.append(f"Policy alignment is {policy_alignment.alignment} under '{policy_alignment.policy_name}'.")
        review_recs.extend(policy_alignment.review_requirements)

    if promotion.consistency == "Review":
        concerns.append("Promotion/level alignment needs review.")
        review_recs.extend(promotion.recommendations)

    if executive_review.review_level != "Standard":
        review_recs.append(
            f"Route through {executive_review.review_level} review: "
            f"{', '.join(executive_review.required_approvers())}."
        )

    governance_notes = governance_mod.build_governance_notes(
        context, compression, inversion, policy_alignment, executive_review
    )

    return FairnessAssessment(
        assessment=assessment,
        concerns=list(dict.fromkeys(concerns)) or ["No material fairness concerns surfaced from the available data."],
        human_review_recommendations=list(dict.fromkeys(r for r in review_recs if r)) or ["No human review required beyond standard approvals."],
        governance_notes=governance_notes,
        evidence=list(dict.fromkeys(evidence)),
        assumptions=assumptions or ["Assessment rests on the connected data and the existing intelligence signals."],
    )
