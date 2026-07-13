"""Shared presentation helpers for the TalentMind UI layer.

This module holds only formatting/caching utilities used across the Streamlit
UI modules. No scoring, ranking, or ML logic lives here — it merely reuses the
existing engine outputs. Centralizing these helpers removes the badge and
action-count logic that was previously copy-pasted across ``app.py``.
"""

from typing import Dict

import streamlit as st

from src.models.candidates import Candidate
from src.intelligence.candidate.engine import build_candidate_intelligence
from src.intelligence.candidate.models import CandidateIntelligence

# Match-badge thresholds — unchanged from the original app.py inline logic.
STRONG_MATCH_THRESHOLD: int = 170
GOOD_MATCH_THRESHOLD: int = 140


def calculate_badge(score: float) -> str:
    """Return the match badge for a hybrid score.

    Thresholds are identical to the original inline logic (>=170 Strong,
    >=140 Good, otherwise Weak).
    """
    if score >= STRONG_MATCH_THRESHOLD:
        return "🟢 Strong Match"
    if score >= GOOD_MATCH_THRESHOLD:
        return "🟡 Good Match"
    return "🔴 Weak Match"


def count_actions(actions: Dict[str, str]) -> Dict[str, int]:
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
