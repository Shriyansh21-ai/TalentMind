"""Career Timeline tab renderer for TalentMind.

Presentation only: renders a :class:`CareerTimelineAnalysis` with progress
meters, trajectory indicators, the career narrative, and strength/concern
cards. All analysis is precomputed by the timeline engine and injected here.
"""

import streamlit as st

from src.intelligence.timeline.models import CareerTimelineAnalysis
from src.ui.components import render_cards, render_meter


def render_timeline_tab(analysis: CareerTimelineAnalysis) -> None:
    """Render the Career Timeline tab from a precomputed analysis."""
    st.subheader("📈 Career Timeline Intelligence")
    st.caption(analysis.timeline_summary)

    top = st.columns(3)
    with top[0]:
        render_meter("Career Progress", analysis.timeline_score)
    with top[1]:
        render_meter("Career Stability", analysis.career_stability)
    with top[2]:
        render_meter("Career Growth", analysis.career_growth_score)

    stats = st.columns(3)
    stats[0].metric("Promotion Velocity", f"{analysis.promotion_velocity:.2f}/yr")
    stats[1].metric("Promotions", analysis.promotion_count)
    stats[2].metric("Job Switches", analysis.job_switches)

    detail = st.columns(3)
    detail[0].metric("Avg Tenure", f"{analysis.average_job_duration:.0f} mo")
    detail[1].metric("Domain Consistency", f"{analysis.domain_consistency:.0f}%")
    detail[2].metric("Leadership", analysis.leadership_progression)

    st.metric("Company Quality Trend", analysis.company_quality_trend)

    st.divider()

    st.markdown("### 🧭 Career Story")
    st.info(analysis.career_story)

    left, right = st.columns(2)
    with left:
        st.markdown("### 💪 Trajectory Strengths")
        render_cards(
            analysis.strengths,
            style="success",
            empty_message="No standout trajectory strengths detected.",
        )
    with right:
        st.markdown("### ⚠ Trajectory Concerns")
        render_cards(
            analysis.concerns,
            style="warning",
            empty_message="No trajectory concerns detected.",
        )
