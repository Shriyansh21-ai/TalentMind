"""Interview Plan tab renderer (Module 4 UI).

Renders a deterministic :class:`InterviewPlan` as a structured, recruiter-ready
interview guide. Pure presentation — the plan is computed upstream and injected.
"""

from __future__ import annotations

import streamlit as st

from src.interview.models import InterviewPlan


def _section(title: str, items: list[str], icon: str = "•") -> None:
    """Render a titled bullet section if it has content."""
    if not items:
        return
    st.markdown(f"**{title}**")
    for item in items:
        st.write(icon, item)


def render_interview_tab(plan: InterviewPlan) -> None:
    """Render the full interview plan.

    Args:
        plan: The deterministic interview plan for the candidate.
    """
    st.subheader("Structured Interview Plan")
    st.caption("Generated deterministically from candidate intelligence — no LLM.")

    left, right = st.columns(2)

    with left:
        _section("Technical Topics", plan.technical_topics, "")
        _section("System Design", plan.system_design_topics, "")
        _section("Coding Focus", plan.coding_focus, "")
        _section("Deep-Dive Topics", plan.deep_dive_topics, "")

    with right:
        _section("Behavioral Questions", plan.behavioral_questions, "")
        _section("Leadership Questions", plan.leadership_questions, "")
        _section("Communication Focus", plan.communication_focus, "")

    st.divider()

    v, r = st.columns(2)
    with v:
        _section("Validation Questions", plan.validation_questions, "")
    with r:
        _section("Risk Follow-ups", plan.risk_followups, "")
