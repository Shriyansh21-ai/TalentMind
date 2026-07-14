"""Top-ranked candidate card rendering for TalentMind.

Renders a single ranked candidate: the summary header, ranking reasons, pipeline
status, a compare toggle, the enterprise pipeline controls, and an expander
containing the full profile tabs.

As of Phase 2 / Milestone 2 the per-candidate engine outputs are sourced from the
shared, cached :class:`CandidateInsights` bundle (see ``src/ui/helpers.py``) so
the card, the profile tabs, the interview plan and the enterprise workspace all
share one computation per candidate. No scoring or ranking logic runs here.
"""

import streamlit as st

from src.models.candidates import Candidate
from src.recruiter.pipeline import get_status
from src.interview.planner import build_interview_plan
from src.ui.helpers import calculate_badge, get_insights
from src.ui.pipeline_controls import render_pipeline_controls
from src.ui.profile_tabs import render_profile_tabs
from src.ui.workspace_state import is_selected, toggle_compare


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
    insights = get_insights(candidate, jd, score)
    explanation = insights.explanation
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

        # --- Compare toggle (feeds the Comparison workspace) ---------------
        selected = is_selected(candidate.candidate_id)
        compare_label = "✓ Comparing" if selected else "➕ Compare"
        if st.button(compare_label, key=f"compare_{candidate.candidate_id}"):
            toggle_compare(candidate.candidate_id)
            _rerun()

        status = get_status(candidate.candidate_id)
        st.caption(f"Pipeline Status: {status}")

        with st.expander("View Candidate"):
            render_pipeline_controls(candidate)
            st.divider()

            st.metric("Overall Match Score", score)

            interview_plan = build_interview_plan(insights)

            render_profile_tabs(
                candidate=candidate,
                score=score,
                badge=badge,
                explanation=explanation,
                intel=insights.intelligence,
                gap=insights.gap,
                summary=insights.summary,
                recommendation=insights.recommendation,
                timeline=insights.timeline,
                risk=insights.risk,
                interview_plan=interview_plan,
                insights=insights,
                jd=jd,
            )

    st.divider()


def _rerun() -> None:
    """Trigger a Streamlit rerun, tolerant of Streamlit version differences."""
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun is not None:
        rerun()
