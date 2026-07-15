"""Interview decision matrix (Module 8).

Builds the Strong Hire / Hire / Hold / Reject bands with the signals, evidence
and confidence each rests on, plus escalation criteria and an explicit statement
of how the matrix aligns with the AI Hiring Committee's decision. The studio does
**not** re-decide the hire — it maps *interview outcomes* onto bands and defers
to the committee's authoritative recommendation for alignment (Modules 8 / 16).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.interview_studio.schemas import DecisionBand, DecisionMatrix


def _confidence_label(evidence: Dict[str, Any]) -> str:
    """Return a qualitative confidence label from the strongest source."""
    committee = evidence.get("committee") or {}
    overall = (committee.get("confidence") or {}).get("overall")
    if overall is None:
        overall = (evidence.get("intelligence") or {}).get("confidence")
    if not isinstance(overall, (int, float)):
        return "Moderate"
    if overall >= 75:
        return "High"
    if overall >= 55:
        return "Moderate"
    return "Low"


def _committee_alignment(evidence: Dict[str, Any]) -> str:
    """State how the matrix aligns with the committee (or the recommendation)."""
    committee = evidence.get("committee") or {}
    consensus = committee.get("consensus") or {}
    rec = consensus.get("recommendation")
    level = consensus.get("level")
    if rec:
        return (
            f"The AI Hiring Committee reached '{rec}'"
            + (f" ({level} consensus)" if level else "")
            + ". This matrix maps the interview outcome onto that decision; a "
            "final band that contradicts the committee should be escalated with evidence."
        )
    recommendation = evidence.get("recommendation") or {}
    if recommendation.get("recommendation"):
        return (
            f"The Hiring Recommendation engine suggested '{recommendation['recommendation']}'. "
            "The interview should confirm or, with evidence, revise it."
        )
    return "No committee decision was available; the interview outcome is the primary signal."


def build_decision_matrix(evidence: Dict[str, Any]) -> DecisionMatrix:
    """Assemble the :class:`DecisionMatrix` for a candidate (deterministic)."""
    conf = _confidence_label(evidence)

    bands = [
        DecisionBand(
            label="Strong Hire",
            signals=[
                "Exceeds the bar on the critical rubric dimensions",
                "Deep, verifiable evidence across technical and behavioral rounds",
                "No unresolved red flags",
            ],
            evidence=[
                "Multiple 'Strong' rubric ratings, including the critical dimensions",
                "Risk-validation questions all passed convincingly",
            ],
            confidence_label=conf,
            escalation="Fast-track to offer; align level and comp with the committee band.",
        ),
        DecisionBand(
            label="Hire",
            signals=[
                "Meets the bar on the critical dimensions",
                "Solid evidence with at most minor gaps",
                "Any flagged risks were adequately addressed",
            ],
            evidence=[
                "Mostly 'Solid'/'Strong' rubric ratings",
                "Risk validations passed or explained",
            ],
            confidence_label=conf,
            escalation="Proceed to offer; note any gap for onboarding.",
        ),
        DecisionBand(
            label="Hold",
            signals=[
                "Mixed evidence — strong in some areas, unproven in others",
                "A material question remains open after the loop",
                "Risk validation was inconclusive",
            ],
            evidence=[
                "'Mixed' ratings on one or more critical dimensions",
                "At least one risk validation neither passed nor clearly failed",
            ],
            confidence_label="Low" if conf == "High" else conf,
            escalation="Add a targeted follow-up round or bar-raiser before deciding.",
        ),
        DecisionBand(
            label="Reject",
            signals=[
                "Misses the bar on a critical dimension",
                "Red flags confirmed rather than resolved",
                "Insufficient depth for the role's seniority",
            ],
            evidence=[
                "'Weak' rating on a critical dimension",
                "A risk validation failed",
            ],
            confidence_label=conf,
            escalation="Decline; capture specific, evidence-based reasons for the candidate record.",
        ),
    ]

    escalation_criteria = [
        "The interview outcome contradicts the AI Hiring Committee's recommendation",
        "Panelists disagree materially on a critical dimension",
        "A high-severity risk was neither confirmed nor cleared",
        "Confidence is Low despite a completed loop",
    ]

    return DecisionMatrix(
        bands=bands,
        escalation_criteria=escalation_criteria,
        committee_alignment=_committee_alignment(evidence),
    )
