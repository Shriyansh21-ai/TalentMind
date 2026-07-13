"""Resume Risk tab renderer for TalentMind.

Presentation only: renders a :class:`RiskReport` with an overall risk meter,
level badge, per-dimension sub-risk badges, red-flag and positive-signal
cards, and recruiter validation questions. Analysis is injected precomputed.
"""

import streamlit as st

from src.intelligence.risk.models import RiskReport
from src.ui.components import render_cards, render_level_badge, render_meter


def render_risk_tab(report: RiskReport) -> None:
    """Render the Risk Analysis tab from a precomputed report."""
    st.subheader("🚨 Resume Risk Analysis")

    header = st.columns([1, 1])
    with header[0]:
        render_meter(
            "Overall Risk Score",
            report.risk_score,
            help_text="Higher means more items to validate (0-100).",
        )
    with header[1]:
        render_level_badge("Risk Level", report.risk_level)
        st.caption(report.overall_risk)
        st.metric("Career Consistency", f"{report.career_consistency:.0f}%")

    st.divider()

    st.markdown("### 🎛 Risk Breakdown")
    row1 = st.columns(3)
    with row1[0]:
        render_level_badge("Employment Gaps", report.employment_gap_risk)
    with row1[1]:
        render_level_badge("Job Hopping", report.job_hopping_risk)
    with row1[2]:
        render_level_badge("Skill Stagnation", report.skill_stagnation_risk)

    row2 = st.columns(3)
    with row2[0]:
        render_level_badge("Technical Depth", report.technical_depth_risk)
    with row2[1]:
        render_level_badge("Leadership", report.leadership_risk)
    with row2[2]:
        render_level_badge("Communication", report.communication_risk)

    st.divider()

    left, right = st.columns(2)
    with left:
        st.markdown("### 🚩 Red Flags")
        render_cards(
            report.red_flags,
            style="error",
            empty_message="No red flags detected.",
        )
    with right:
        st.markdown("### ✅ Positive Signals")
        render_cards(
            report.positive_signals,
            style="success",
            empty_message="No mitigating signals detected.",
        )

    if report.risk_factors:
        st.markdown("### 🔎 Contributing Factors")
        render_cards(report.risk_factors, style="warning")

    st.markdown("### ❓ Recommended Validation Questions")
    render_cards(
        report.validation_questions,
        style="info",
        empty_message="No specific validation questions — proceed with a standard screen.",
    )
