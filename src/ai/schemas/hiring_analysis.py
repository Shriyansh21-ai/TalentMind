"""Structured output schema for the HiringAnalystAgent.

The schema deliberately contains **no numeric score fields**. This is a
structural safety guarantee: the AI reasoning layer physically cannot emit or
override any deterministic score — it can only produce human-quality narrative
reasoning *about* the scores computed by the existing engines.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# Allowed executive verdicts. The AI may only *narrate* a decision; the canonical
# recommendation still comes from the deterministic recommendation engine.
EXECUTIVE_DECISIONS = ["Strong Hire", "Hire", "Hold", "Reject", "Insufficient Evidence"]


class HiringAnalysis(BaseAIResponse):
    """Narrative hiring analysis produced by reasoning over structured intelligence.

    Attributes:
        executive_summary: 2-4 sentence summary for a busy hiring leader.
        overall_reasoning: Holistic reasoning tying the signals together.
        technical_reasoning: Reasoning about technical capability evidence.
        career_reasoning: Reasoning about the career trajectory / growth.
        leadership_reasoning: Reasoning about leadership signals.
        risk_reasoning: Reasoning about the risk report (what to validate).
        jd_alignment: How the candidate aligns to the job description.
        hidden_strengths: Non-obvious strengths implied by the evidence.
        hidden_concerns: Non-obvious concerns implied by the evidence.
        transferable_skills: Skills that transfer to the target role.
        interview_strategy: Concrete, ordered interview strategy items.
        business_impact: Expected business impact framing.
        confidence_reasoning: Why the analysis is / isn't confident, incl. any
            explicit uncertainty when evidence is thin.
        executive_decision: One of :data:`EXECUTIVE_DECISIONS` (narrative verdict).
    """

    executive_summary: str
    overall_reasoning: str
    technical_reasoning: str
    career_reasoning: str
    leadership_reasoning: str
    risk_reasoning: str
    jd_alignment: str
    hidden_strengths: list[str] = Field(default_factory=list)
    hidden_concerns: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    interview_strategy: list[str] = Field(default_factory=list)
    business_impact: str
    confidence_reasoning: str
    executive_decision: str

    @field_validator("executive_decision")
    @classmethod
    def _validate_decision(cls, value: str) -> str:
        """Coerce the decision to a known verdict (tolerant of extra text)."""
        text = (value or "").strip()
        for decision in EXECUTIVE_DECISIONS:
            if decision.lower() in text.lower():
                return decision
        # Unknown verdict -> the platform's honest default.
        return "Insufficient Evidence"

    @field_validator(
        "executive_summary",
        "overall_reasoning",
        "technical_reasoning",
        "career_reasoning",
        "leadership_reasoning",
        "risk_reasoning",
        "jd_alignment",
        "business_impact",
        "confidence_reasoning",
    )
    @classmethod
    def _non_empty(cls, value: str) -> str:
        """Ensure narrative fields are non-empty strings."""
        text = (value or "").strip()
        if not text:
            raise ValueError("narrative field must not be empty")
        return text
