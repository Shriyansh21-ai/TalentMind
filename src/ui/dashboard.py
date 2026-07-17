"""Recruiter dashboard metrics for TalentMind.

Renders the pipeline overview. Each distinct metric is shown exactly once
(the original app.py rendered several metrics twice); every displayed value is
computed identically to the original.
"""

import streamlit as st

from src.models.candidates import Candidate
from src.ui.helpers import count_actions


def render_dashboard(
    candidates: list[Candidate],
    results: list[tuple[Candidate, float]],
    jd: str,
    actions: dict[str, str],
) -> None:
    """Render the recruiter dashboard metric row.

    Args:
        candidates: Full candidate pool.
        results: Ranked ``(candidate, score)`` tuples (highest first).
        jd: Raw job-description text.
        actions: Recruiter pipeline action map (``candidate_id -> status``).
    """
    st.header("Dashboard")

    tallies = count_actions(actions)
    best_match = results[0][1] if results else 0

    top = st.columns(4)
    top[0].metric("Candidates", f"{len(candidates):,}")
    top[1].metric("Ranked", f"{len(results):,}")
    top[2].metric("Best Match", best_match)
    top[3].metric("JD Length", len(jd))

    bottom = st.columns(4)
    bottom[0].metric("Shortlisted", tallies["Shortlisted"])
    bottom[1].metric("Interview", tallies["Interview"])
    bottom[2].metric("Rejected", tallies["Rejected"])
    bottom[3].metric("Hired", tallies["Hired"])

    st.divider()
