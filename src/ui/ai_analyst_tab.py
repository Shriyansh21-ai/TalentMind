"""AI Hiring Analyst profile tab (Module 10).

Renders the :class:`HiringAnalysis` produced by the AI Platform for one
candidate. Generation is strictly on-demand: on open the tab shows a previously
cached analysis (if any) instantly via a provider-free cache peek; otherwise the
recruiter clicks a button to generate one. This keeps the AI out of the ranking
path entirely (Module 11).

Presentation only — all reasoning comes from the service facade.
"""

from __future__ import annotations

from typing import List

import streamlit as st

from src.insights.models import CandidateInsights
from src.interview.models import InterviewPlan
from src.ai.core.response import AgentResult, AgentStatus
from src.ai.schemas.hiring_analysis import HiringAnalysis
from src.ai.services.hiring_analyst_service import (
    analyze_candidate,
    get_platform_status,
    peek_cached_analysis,
)

_DECISION_STYLE = {
    "Strong Hire": ("success", "🟢"),
    "Hire": ("info", "🔵"),
    "Hold": ("warning", "🟡"),
    "Reject": ("error", "🔴"),
    "Insufficient Evidence": ("warning", "⚪"),
}


def render_ai_analyst_tab(
    candidate_id: str,
    insights: CandidateInsights,
    interview_plan: InterviewPlan,
    jd: str,
) -> None:
    """Render the AI Hiring Analyst tab for one candidate.

    Args:
        candidate_id: The candidate id (used for widget keys).
        insights: The candidate's shared insight bundle.
        interview_plan: The candidate's deterministic interview plan.
        jd: Raw job-description text.
    """
    st.subheader("🤖 AI Hiring Analyst")

    status = get_platform_status()
    st.caption(
        f"Provider: **{status['provider']}** · Model: **{status['model']}** · "
        "Reasoning over deterministic intelligence — no scores are computed or "
        "changed by the AI."
    )

    # On-demand only: try a provider-free cache peek first.
    result = peek_cached_analysis(insights, interview_plan, jd)

    controls = st.columns([1, 1, 3])
    with controls[0]:
        generate = st.button("✨ Generate", key=f"ai_gen_{candidate_id}")
    with controls[1]:
        refresh = st.button(
            "♻ Refresh",
            key=f"ai_refresh_{candidate_id}",
            disabled=result is None,
            help="Recompute and overwrite the cached analysis.",
        )

    if generate or refresh:
        with st.spinner("Generating AI hiring analysis..."):
            result = analyze_candidate(
                insights, interview_plan, jd, force_refresh=bool(refresh)
            )

    if result is None:
        st.info(
            "No AI analysis yet. Click **Generate** to produce an executive "
            "hiring analysis from the candidate's structured intelligence."
        )
        return

    if not result.ok:
        st.error(f"AI analysis unavailable: {result.error}")
        return

    _render_status_line(result)
    _render_analysis(result.data)


def _render_status_line(result: AgentResult) -> None:
    """Render a small provenance/telemetry line for the analysis."""
    badge = {
        AgentStatus.SUCCESS: "🟢 generated",
        AgentStatus.CACHED: "💾 cached",
        AgentStatus.FALLBACK: "🟡 deterministic fallback",
    }.get(result.status, result.status.value)

    bits = [
        badge,
        f"provider: {result.provider}",
        f"latency: {result.latency_ms:.0f} ms",
    ]
    if result.usage.total_tokens:
        bits.append(f"tokens: {result.usage.total_tokens}")
    st.caption(" · ".join(bits))

    for warning in result.warnings:
        st.caption(f"⚠ {warning}")


def _render_analysis(analysis: HiringAnalysis) -> None:
    """Render the full analysis with collapsible sections."""
    # Executive verdict banner.
    style, emoji = _DECISION_STYLE.get(analysis.executive_decision, ("info", "⚪"))
    renderer = {
        "success": st.success,
        "info": st.info,
        "warning": st.warning,
        "error": st.error,
    }.get(style, st.info)
    renderer(f"{emoji} Executive Decision: **{analysis.executive_decision}**")

    st.markdown("### Executive Summary")
    st.write(analysis.executive_summary)

    with st.expander("🧭 Overall Analysis", expanded=True):
        st.write(analysis.overall_reasoning)

    with st.expander("🧪 Technical Assessment"):
        st.write(analysis.technical_reasoning)

    with st.expander("📈 Career Assessment"):
        st.write(analysis.career_reasoning)

    with st.expander("👥 Leadership Assessment"):
        st.write(analysis.leadership_reasoning)

    with st.expander("🚨 Risk Assessment"):
        st.write(analysis.risk_reasoning)

    with st.expander("🎯 JD Alignment"):
        st.write(analysis.jd_alignment)

    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("💡 Hidden Strengths", expanded=True):
            _bullets(analysis.hidden_strengths, "No hidden strengths surfaced.")
        with st.expander("🔁 Transferable Skills"):
            _bullets(analysis.transferable_skills, "None identified.")
    with col_b:
        with st.expander("⚠ Hidden Concerns", expanded=True):
            _bullets(analysis.hidden_concerns, "No hidden concerns surfaced.")

    with st.expander("🗺 Interview Strategy"):
        _bullets(analysis.interview_strategy, "No strategy items generated.")

    with st.expander("💼 Business Impact"):
        st.write(analysis.business_impact)

    with st.expander("📊 Confidence"):
        st.write(analysis.confidence_reasoning)


def _bullets(items: List[str], empty_message: str) -> None:
    """Render a bullet list, or a caption when empty."""
    if not items:
        st.caption(empty_message)
        return
    for item in items:
        st.write("•", item)
