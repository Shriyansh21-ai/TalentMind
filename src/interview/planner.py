"""Deterministic interview-plan generation (Module 4).

Builds an :class:`InterviewPlan` from the shared :class:`CandidateInsights`
bundle using explicit, threshold-based heuristics. There is **no LLM** here and
no I/O — the same candidate always yields the same plan, which keeps the feature
cheap, auditable and unit-testable.
"""

from __future__ import annotations

from typing import List

from src.insights.models import CandidateInsights
from src.interview.models import InterviewPlan

# Seniority / capability thresholds (0-100 engine scales, years for experience).
SENIOR_YEARS = 8.0
MID_YEARS = 4.0
STRONG_TECH = 75.0
STRONG_LEADERSHIP = 70.0
MODERATE_LEADERSHIP = 45.0

# Cap list lengths so the rendered plan stays scannable.
_MAX_TOPICS = 6


def _top_skills(insights: CandidateInsights, limit: int = 5) -> List[str]:
    """Return the candidate's highest-signal skills (by endorsements, then name).

    Falls back to declaration order when endorsements are unavailable.
    """
    skills = sorted(
        insights.candidate.skills,
        key=lambda s: (getattr(s, "endorsements", 0), getattr(s, "duration_months", 0)),
        reverse=True,
    )
    return [s.name for s in skills[:limit]]


def _technical_topics(insights: CandidateInsights) -> List[str]:
    """Blend proven skills with JD gaps to probe both depth and coverage."""
    topics: List[str] = []
    for skill in _top_skills(insights, limit=4):
        topics.append(f"Depth in {skill}")
    for skill in insights.missing_skills[:2]:
        topics.append(f"Exposure to {skill} (JD gap)")
    if not topics:
        topics.append("Core computer-science fundamentals")
    return topics[:_MAX_TOPICS]


def _system_design_topics(insights: CandidateInsights) -> List[str]:
    """Scale system-design scope to the candidate's seniority."""
    years = insights.years_of_experience
    if years >= SENIOR_YEARS:
        return [
            "Design a large-scale distributed system end-to-end",
            "Trade-offs: consistency, availability, partitioning",
            "Scaling bottlenecks and capacity planning",
            "Failure modes, observability and recovery",
        ]
    if years >= MID_YEARS:
        return [
            "Design a service with a clean API boundary",
            "Data modelling and storage choices",
            "Caching and basic scaling strategies",
        ]
    return [
        "Component-level design of a small feature",
        "Reasoning about data structures and APIs",
    ]


def _behavioral_questions(insights: CandidateInsights) -> List[str]:
    """Standard behavioral set, tailored by the candidate's weaknesses."""
    questions = [
        "Tell me about a project you are most proud of and your specific role.",
        "Describe a disagreement with a colleague and how you resolved it.",
        "How do you prioritize when everything feels urgent?",
    ]
    for weakness in insights.intelligence.weaknesses[:2]:
        questions.append(f"Walk me through how you've handled: {weakness}")
    return questions[:_MAX_TOPICS]


def _leadership_questions(insights: CandidateInsights) -> List[str]:
    """Depth of leadership probing scales with the leadership score."""
    score = insights.intelligence.leadership_score
    if score >= STRONG_LEADERSHIP:
        return [
            "Describe a team you built or grew and the outcomes.",
            "How do you develop and mentor engineers under you?",
            "Tell me about a hard people decision you made.",
            "How do you set technical direction across teams?",
        ]
    if score >= MODERATE_LEADERSHIP:
        return [
            "Have you led a project or mentored peers? What did you learn?",
            "How do you influence without formal authority?",
        ]
    return [
        "Describe a time you took ownership beyond your assigned task.",
        "How do you see your growth toward a leadership role?",
    ]


def _deep_dive_topics(insights: CandidateInsights) -> List[str]:
    """The candidate's strongest signals — where to go deep."""
    topics = [f"Deep dive: {strength}" for strength in insights.intelligence.strengths[:3]]
    top = _top_skills(insights, limit=2)
    for skill in top:
        topics.append(f"Real-world application of {skill}")
    if not topics:
        topics.append("Deep dive into the candidate's most recent project")
    return topics[:_MAX_TOPICS]


def _coding_focus(insights: CandidateInsights) -> List[str]:
    """Calibrate the coding round to demonstrated technical strength."""
    tech = insights.intelligence.technical_score
    if tech >= STRONG_TECH:
        return [
            "Non-trivial algorithmic problem with optimization discussion",
            "Code quality, testing and edge-case handling",
        ]
    return [
        "Fundamental data-structure / algorithm problem",
        "Readable, correct implementation with clear reasoning",
        "Debugging a provided snippet",
    ]


def _communication_focus(insights: CandidateInsights) -> List[str]:
    """Communication assessment, escalated when risk analysis flags it."""
    focus = [
        "Clarity when explaining technical trade-offs",
        "Structured, concise answers under ambiguity",
    ]
    if insights.risk.communication_risk in {"Medium", "High"}:
        focus.insert(
            0,
            "Probe written/verbal communication — risk analysis flagged a gap.",
        )
    return focus[:_MAX_TOPICS]


def _validation_and_risk(insights: CandidateInsights):
    """Return (validation_questions, risk_followups) sourced from risk analysis."""
    risk = insights.risk
    validation = list(risk.validation_questions[:_MAX_TOPICS])
    if not validation:
        validation = ["Confirm scope and personal contribution on key projects."]

    followups: List[str] = []
    for flag in risk.red_flags[:3]:
        followups.append(f"Address red flag: {flag}")
    for factor in risk.risk_factors[:2]:
        followups.append(f"Clarify: {factor}")
    if not followups:
        followups = ["No material red flags — confirm baseline expectations only."]
    return validation, followups[:_MAX_TOPICS]


def build_interview_plan(insights: CandidateInsights) -> InterviewPlan:
    """Generate a full :class:`InterviewPlan` for one candidate (deterministic).

    Args:
        insights: The shared insight bundle for the candidate.

    Returns:
        A populated :class:`InterviewPlan`.
    """
    validation, risk_followups = _validation_and_risk(insights)

    return InterviewPlan(
        technical_topics=_technical_topics(insights),
        system_design_topics=_system_design_topics(insights),
        behavioral_questions=_behavioral_questions(insights),
        leadership_questions=_leadership_questions(insights),
        validation_questions=validation,
        deep_dive_topics=_deep_dive_topics(insights),
        coding_focus=_coding_focus(insights),
        communication_focus=_communication_focus(insights),
        risk_followups=risk_followups,
    )
