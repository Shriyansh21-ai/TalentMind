"""Shared presentation helpers for the TalentMind UI layer.

This module holds only formatting/caching utilities used across the Streamlit
UI modules. No scoring, ranking, or ML logic lives here — it merely reuses the
existing engine outputs. Centralizing these helpers removes the badge and
action-count logic that was previously copy-pasted across ``app.py``.
"""

import streamlit as st

from src.insights.builder import build_insights
from src.insights.models import CandidateInsights
from src.intelligence.candidate.engine import build_candidate_intelligence
from src.intelligence.candidate.models import CandidateIntelligence
from src.intelligence.risk.analyzer import build_risk_report
from src.intelligence.risk.models import RiskReport
from src.intelligence.timeline.analyzer import build_career_timeline
from src.intelligence.timeline.models import CareerTimelineAnalysis
from src.models.candidates import Candidate

# Match-badge thresholds — unchanged from the original app.py inline logic.
STRONG_MATCH_THRESHOLD: int = 170
GOOD_MATCH_THRESHOLD: int = 140


def calculate_badge(score: float) -> str:
    """Return the match badge for a hybrid score.

    Thresholds are identical to the original inline logic (>=170 Strong,
    >=140 Good, otherwise Weak).
    """
    if score >= STRONG_MATCH_THRESHOLD:
        return "Strong Match"
    if score >= GOOD_MATCH_THRESHOLD:
        return "Good Match"
    return "Weak Match"


def count_actions(actions: dict[str, str]) -> dict[str, int]:
    """Tally recruiter pipeline actions into per-status counts.

    Counting logic is identical to the original dashboard block.
    """
    return {
        "Shortlisted": sum(1 for x in actions.values() if x == "Shortlisted"),
        "Interview": sum(1 for x in actions.values() if x == "Interview"),
        "Rejected": sum(1 for x in actions.values() if x == "Rejected"),
        "Hired": sum(1 for x in actions.values() if x == "Hired"),
    }


@st.cache_data(hash_funcs={Candidate: lambda c: c.candidate_id})
def get_candidate_intelligence(candidate: Candidate) -> CandidateIntelligence:
    """Cached wrapper around ``build_candidate_intelligence``.

    The returned object is exactly what the intelligence engine produces; the
    cache (keyed by ``candidate_id``) only prevents the same candidate's
    intelligence from being recomputed across Streamlit reruns. No logic is
    changed.
    """
    return build_candidate_intelligence(candidate)


@st.cache_data(hash_funcs={Candidate: lambda c: c.candidate_id})
def get_career_timeline(candidate: Candidate) -> CareerTimelineAnalysis:
    """Cached wrapper around ``build_career_timeline`` (keyed by candidate_id).

    Ensures each candidate's timeline analysis runs at most once per session.
    """
    return build_career_timeline(candidate)


@st.cache_data(hash_funcs={Candidate: lambda c: c.candidate_id})
def get_risk_report(candidate: Candidate) -> RiskReport:
    """Cached wrapper around ``build_risk_report`` (keyed by candidate_id).

    Ensures each candidate's risk analysis runs at most once per session.
    """
    return build_risk_report(candidate)


@st.cache_data(hash_funcs={Candidate: lambda c: c.candidate_id})
def get_insights(candidate: Candidate, jd: str, match_score: float = 0.0) -> CandidateInsights:
    """Cached wrapper around :func:`build_insights` (keyed by candidate + jd).

    This is the single entry point the entire Enterprise Workspace uses to obtain
    a candidate's analytics bundle. Because it is cached by ``(candidate_id, jd,
    match_score)``, the expensive intelligence / timeline / risk engines run at
    most once per candidate per job description per session — the card view, the
    dashboard, comparison, talent-pool segmentation, interview plans and the
    filters all share this one computation.
    """
    return build_insights(candidate, jd=jd, match_score=match_score)
