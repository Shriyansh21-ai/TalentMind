"""Data model for Interview Intelligence (Module 4)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class InterviewPlan:
    """A structured, recruiter-facing interview plan for a single candidate.

    Produced by deterministic heuristics over the candidate's insight bundle —
    no LLM is involved. Each list is ordered most-important-first and safe to
    render directly.

    Attributes:
        technical_topics: Core technical areas to probe (from proven skills).
        system_design_topics: Architecture / design areas (seniority-scaled).
        behavioral_questions: Culture & collaboration questions.
        leadership_questions: People / ownership questions (depth scales with
            demonstrated leadership).
        validation_questions: Questions that verify claims flagged by risk
            analysis.
        deep_dive_topics: The candidate's strongest areas to explore in depth.
        coding_focus: Concrete coding-round focus areas.
        communication_focus: Communication signals to assess.
        risk_followups: Direct follow-ups on detected red flags / concerns.
    """

    technical_topics: list[str] = field(default_factory=list)
    system_design_topics: list[str] = field(default_factory=list)
    behavioral_questions: list[str] = field(default_factory=list)
    leadership_questions: list[str] = field(default_factory=list)
    validation_questions: list[str] = field(default_factory=list)
    deep_dive_topics: list[str] = field(default_factory=list)
    coding_focus: list[str] = field(default_factory=list)
    communication_focus: list[str] = field(default_factory=list)
    risk_followups: list[str] = field(default_factory=list)
