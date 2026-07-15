"""Human vs AI responsibility matrix (Module 5).

Combines the AI decision points (committee vote, compensation/pay-equity/compliance
assessments, the recommendation engine) with the human decision points (approvals,
from :mod:`human_review`) into one matrix that **clearly separates** who is
responsible for what — AI recommendations vs. human overrides/approvals. It never
blurs responsibility and never attributes an unverified human action as observed
(Modules 5 / 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.audit import human_review
from src.ai.agents.audit.schemas import DecisionResponsibility

# AI decision points keyed by the evidence source that proves they occurred.
_AI_DECISIONS = [
    ("AI Hiring Committee", "Committee recommendation", "Committee vote"),
    ("Hiring Recommendation engine", "Hiring recommendation", "AI recommendation"),
    ("Compensation Governance Agent", "Compensation recommendation", "AI recommendation"),
    ("Pay Equity Guardian", "Pay-equity assessment", "AI recommendation"),
    ("Hiring Compliance", "Compliance assessment", "AI recommendation"),
]


def build_responsibility_matrix(context: Dict[str, Any]) -> List[DecisionResponsibility]:
    """Build the Human vs AI responsibility matrix (Module 5)."""
    sources = set(context.get("evidence_sources", []))
    matrix: List[DecisionResponsibility] = []

    # AI side — attributed to "AI", observed only if the evidence source is present.
    for source, decision, kind in _AI_DECISIONS:
        present = source in sources
        matrix.append(
            DecisionResponsibility(
                decision=decision,
                kind=kind,
                responsible_party="AI",
                status="Observed" if present else "Unavailable",
                detail=f"Produced by {source}." if present else f"{source} did not participate.",
            )
        )

    # Human side — approvals/overrides, kept strictly separate.
    matrix.extend(human_review.build_human_decisions(context))
    return matrix
