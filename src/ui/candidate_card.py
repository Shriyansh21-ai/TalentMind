"""Top-ranked candidate card rendering for TalentMind.

Renders a single ranked candidate: the summary header, ranking reasons,
pipeline status, and an expander containing the full profile tabs. This module
assembles the per-candidate engine outputs (explainability, intelligence,
skill gap, hiring recommendation, AI summary) and hands them to
``render_profile_tabs``. No scoring or ranking logic is performed here.
"""

import streamlit as st

from src.models.candidates import Candidate
from src.scoring.explainability import explain_candidate
from src.scoring.skill_gap import get_skill_gap
from src.llm.recruiter_summary import generate_summary
from src.hiring.recommendation import generate_hiring_recommendation
from src.recruiter.pipeline import get_status
from src.ui.helpers import calculate_badge, get_candidate_intelligence
from src.ui.profile_tabs import render_profile_tabs


def render_candidate_card(
    rank: int,
    candidate: Candidate,
    score: float,
    jd: str,
) -> None:
    """Render one ranked candidate card.

    Args:
        rank: 1-based rank position of the candidate.
        candidate: The candidate to render.
        score: The candidate's hybrid match score.
        jd: Raw job-description text (used for skill-gap analysis).
    """
    explanation = explain_candidate(candidate)
    badge = calculate_badge(score)

    with st.container():
        left, right = st.columns([4, 1])

        with left:
            st.markdown(
                f"""
### #{rank} {candidate.profile.current_title}

**Company:** {candidate.profile.current_company}

**Experience:** {candidate.profile.years_of_experience} years

**Location:** {candidate.profile.location}
"""
            )

        with right:
            st.metric("Score", score)

        if "reasons" in explanation:
            st.write("### Why Ranked High?")
            for reason in explanation["reasons"]:
                st.write("✅", reason)

        status = get_status(candidate.candidate_id)
        st.caption(f"Pipeline Status: {status}")

        with st.expander("View Candidate"):
            intel = get_candidate_intelligence(candidate)
            gap = get_skill_gap(candidate, jd)
            recommendation = generate_hiring_recommendation(candidate, intel, gap)
            summary = generate_summary(candidate, explanation, gap)

            st.metric("Overall Match Score", score)

            render_profile_tabs(
                candidate=candidate,
                score=score,
                badge=badge,
                explanation=explanation,
                intel=intel,
                gap=gap,
                summary=summary,
                recommendation=recommendation,
            )

    st.divider()
