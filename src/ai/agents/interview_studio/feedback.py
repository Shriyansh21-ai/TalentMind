"""Feedback intelligence (Module 10).

Produces structured feedback *templates* — interviewer form, hiring-manager
form, panel form and a candidate-feedback summary template. The studio supplies
the structure only; it never invents interview results or fills in a verdict
(Module 16). Each form is derived from the evaluation rubric so feedback maps
1:1 onto the dimensions the panel scored.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.interview_studio.schemas import FeedbackForms, RubricDimension


def build_feedback_forms(
    rubrics: list[RubricDimension],
    evidence: dict[str, Any],
) -> FeedbackForms:
    """Assemble the four feedback templates from the rubric + evidence.

    Args:
        rubrics: The evaluation rubric dimensions (feedback maps onto these).
        evidence: The aggregated interview evidence dict.

    Returns:
        A populated :class:`FeedbackForms`.
    """
    dim_names = [d.name for d in rubrics]

    interviewer_form = (
        [
            "Overall recommendation (Strong Hire / Hire / Hold / Reject) with one-line rationale",
            "Rate each rubric dimension you assessed (Strong / Solid / Mixed / Weak) with a specific example:",
        ]
        + [f"  - {name}" for name in dim_names]
        + [
            "Strongest signal observed (with evidence)",
            "Biggest concern observed (with evidence)",
            "Questions you did NOT get to (for the next interviewer)",
            "Would you want this person on your team? Why?",
        ]
    )

    hiring_manager_form = (
        [
            "Final disposition and the decision band from the matrix",
            "How the loop resolved the committee's interview priorities:",
        ]
        + [f"  - Priority: {p}" for p in _priorities(evidence)[:3]]
        + [
            "Level / offer-band recommendation and rationale",
            "Onboarding focus for any development areas surfaced",
            "Any escalation triggered (and why)",
        ]
    )

    panel_form = [
        "Consolidated rubric roll-up across all interviewers (per dimension)",
        "Points of agreement across the panel",
        "Points of disagreement and how they were resolved",
        "Risk validations: which passed, which failed, which remain open",
        "Panel decision band + confidence, with alignment to the AI Hiring Committee",
        "Dissenting opinions recorded verbatim",
    ]

    candidate_summary_template = [
        "Thank-you and outcome (kept factual and respectful)",
        "Strengths the panel observed (evidence-based, no scores shared)",
        "Areas to develop (constructive, specific)",
        "Next steps / timeline",
        "(Internal only — not shared: rubric ratings and decision band)",
    ]

    return FeedbackForms(
        interviewer_form=interviewer_form,
        hiring_manager_form=hiring_manager_form,
        panel_form=panel_form,
        candidate_summary_template=candidate_summary_template,
    )


def _priorities(evidence: dict[str, Any]) -> list[str]:
    """Return the committee/recommendation interview priorities (may be empty)."""
    committee = evidence.get("committee") or {}
    priorities = list((committee.get("decision") or {}).get("interview_priorities", []) or [])
    recommendation = evidence.get("recommendation") or {}
    priorities += list(recommendation.get("interview_focus", []) or [])
    if not priorities:
        priorities = ["Confirm role fit and depth"]
    return list(dict.fromkeys(priorities))
