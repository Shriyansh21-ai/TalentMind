"""Builder for the unified :class:`CandidateInsights` bundle.

Composes the existing (unmodified) TalentMind engines into a single bundle so the
Enterprise Hiring Workspace modules can share one computation per candidate.

Design note — no caching lives here on purpose. This module is pure and free of
any Streamlit dependency so it can be unit-tested and reused headless. The UI
layer (``src/ui/helpers.py``) is responsible for wrapping :func:`build_insights`
in ``st.cache_data`` keyed by ``(candidate_id, jd)`` so the expensive engines run
at most once per candidate per session.
"""

from __future__ import annotations

from src.models.candidates import Candidate
from src.insights.models import CandidateInsights

from src.scoring.explainability import explain_candidate
from src.scoring.skill_gap import get_skill_gap
from src.llm.recruiter_summary import generate_summary
from src.hiring.recommendation import generate_hiring_recommendation
from src.intelligence.candidate.engine import build_candidate_intelligence
from src.intelligence.timeline.analyzer import build_career_timeline
from src.intelligence.risk.analyzer import build_risk_report


def build_insights(
    candidate: Candidate,
    jd: str = "",
    match_score: float = 0.0,
) -> CandidateInsights:
    """Compute the full insight bundle for a single candidate.

    Every value is produced by an existing engine and stored unchanged. The only
    ordering constraint is that the recruiter summary and hiring recommendation
    consume the skill-gap and explainability output, so those are computed first.

    Args:
        candidate: The candidate to analyse.
        jd: Raw job-description text used for skill-gap analysis. Defaults to an
            empty string (yielding a zero JD-specific skill match) so the bundle
            can still be built outside a ranking run.
        match_score: The candidate's hybrid match score from the ranking
            pipeline, carried through for display. Defaults to ``0.0``.

    Returns:
        A populated :class:`CandidateInsights` bundle.
    """
    explanation = explain_candidate(candidate)
    gap = get_skill_gap(candidate, jd)

    intelligence = build_candidate_intelligence(candidate)
    timeline = build_career_timeline(candidate)
    risk = build_risk_report(candidate)

    summary = generate_summary(candidate, explanation, gap)
    recommendation = generate_hiring_recommendation(candidate, intelligence, gap)

    return CandidateInsights(
        candidate=candidate,
        match_score=match_score,
        intelligence=intelligence,
        timeline=timeline,
        risk=risk,
        gap=gap,
        explanation=explanation,
        summary=summary,
        recommendation=recommendation,
    )
