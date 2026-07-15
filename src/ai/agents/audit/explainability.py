"""Governance explainability (Module 6).

Produces transparent, evidence-referenced explanations of *why* each governance
event occurred — why an approval was required, why the committee voted, why
compensation was reviewed, why an equity review triggered and why a compliance
review occurred. Explanations restate the reused signals; they make no legal
determination (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.audit.schemas import GovernanceExplanation


def build_governance_explanations(context: Dict[str, Any]) -> List[GovernanceExplanation]:
    """Build the transparent governance explanations (Module 6)."""
    sources = set(context.get("evidence_sources", []))
    approvals = context.get("approvals", {}) or {}
    required = approvals.get("required", [])
    governance_risk = context.get("governance_risk", {}) or {}
    review = context.get("review", {}) or {}
    equity_level = context.get("equity_risk_level", "")

    explanations: List[GovernanceExplanation] = []

    if required:
        reasons = "; ".join(
            a["reason"] for a in approvals.get("approvals", []) if a.get("required")
        )[:400]
        explanations.append(
            GovernanceExplanation(
                topic="Approvals",
                question="Why were these approvals required?",
                explanation=f"Required approvers: {', '.join(required)}. {reasons}",
                register="Observed",
            )
        )

    if "AI Hiring Committee" in sources:
        explanations.append(
            GovernanceExplanation(
                topic="Committee",
                question="Why did the committee vote?",
                explanation=(
                    "The AI Hiring Committee convened to reach an evidence-weighted consensus "
                    "over the resume, JD, intelligence, timeline, risk and interview signals."
                ),
                register="Observed",
            )
        )

    if "Compensation Governance Agent" in sources:
        explanations.append(
            GovernanceExplanation(
                topic="Compensation",
                question="Why was compensation reviewed?",
                explanation=(
                    "Compensation Governance produced a defensible range from the candidate's "
                    "stated expectation and the assessed capability signals."
                ),
                register="Observed",
            )
        )

    if "Pay Equity Guardian" in sources:
        explanations.append(
            GovernanceExplanation(
                topic="Pay equity",
                question="Why did an equity review trigger?",
                explanation=(
                    f"The Pay Equity Guardian assessed internal fairness of the offer"
                    + (f" (equity risk {equity_level})." if equity_level and equity_level != "Unknown"
                       else " (internal data unavailable, so it is provisional).")
                ),
                register="Observed",
            )
        )

    if "Hiring Compliance" in sources:
        explanations.append(
            GovernanceExplanation(
                topic="Compliance",
                question="Why did a compliance review occur?",
                explanation=(
                    f"Hiring Compliance evaluated workflow/approval/policy adherence; governance "
                    f"risk is {governance_risk.get('level', 'Medium')}. "
                    + (review.get("rationale", ""))
                ),
                register="Inferred",
            )
        )

    if not explanations:
        explanations.append(
            GovernanceExplanation(
                topic="Governance",
                question="Why did governance steps occur?",
                explanation="No governance events were evidenced in this decision journey.",
                register="Unavailable",
            )
        )
    return explanations
