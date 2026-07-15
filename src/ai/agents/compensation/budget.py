"""Budget governance (Module 7).

Classifies the hire (Replacement / Growth / Critical), estimates budget
utilization and hiring priority, and states the investment rationale — all as
**heuristic estimates over existing intelligence**, never fabricated financial
metrics (Module 16). Every figure is qualitative or explicitly flagged as an
assumption.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.compensation.schemas import BudgetAssessment, CompensationRange


def _num(source: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def _hire_type(evidence: Dict[str, Any]) -> str:
    """Classify the hire from the hiring stance + role signals (heuristic)."""
    committee = evidence.get("committee") or {}
    stance = str((committee.get("consensus") or {}).get("recommendation", "")) or str(
        (evidence.get("recommendation") or {}).get("recommendation", "")
    )
    intelligence = evidence.get("intelligence") or {}
    leadership = _num(intelligence, "leadership_score")

    if "strong" in stance.lower():
        return "Critical Hire"
    if leadership >= 70:
        return "Critical Hire"
    if "hire" in stance.lower():
        return "Growth Hire"
    return "Growth Hire"


def assess_budget(evidence: Dict[str, Any], band: CompensationRange) -> BudgetAssessment:
    """Assess budget governance for the recommendation (Module 7)."""
    hire_type = _hire_type(evidence)
    intelligence = evidence.get("intelligence") or {}
    overall = _num(intelligence, "overall_score")

    assumptions: List[str] = [
        "No department budget or headcount plan is connected; utilization is a "
        "qualitative estimate, not a financial metric.",
    ]

    if hire_type == "Critical Hire":
        priority = "High"
        utilization = "Justifies top-of-band"
        investment = (
            "A critical/strategic hire: the recommended range (up to "
            f"{band.maximum:.1f} {band.unit}) is defensible given the assessed impact."
        )
    elif overall >= 70:
        priority = "Elevated"
        utilization = "Within band, upper half"
        investment = "A strong growth hire; investing at or above target is defensible."
    else:
        priority = "Standard"
        utilization = "Within band"
        investment = "A standard growth hire; anchor near target and preserve headroom."

    reasons = list((evidence.get("recommendation") or {}).get("reasons", []))
    justification = (
        "Business justification: " + "; ".join(reasons[:3]) + "."
        if reasons
        else "Business justification rests on the candidate-intelligence signals and role fit."
    )

    confidence = 55.0 + (10.0 if evidence.get("committee") else 0.0) + (10.0 if reasons else 0.0)
    confidence = min(100.0, confidence)

    return BudgetAssessment(
        hire_type=hire_type,
        budget_utilization=utilization,
        hiring_priority=priority,
        investment_rationale=investment,
        business_justification=justification,
        confidence=round(confidence, 1),
        assumptions=assumptions,
    )
