"""Resume Intelligence dashboard (Module 13).

A professional, enterprise UI over the :class:`ResumeAnalysis` produced by the
ResumeAnalystAgent: quality dimensions with progress bars + a chart, an executive
summary, strengths/weaknesses, career narrative, writing analysis, project
intelligence, an evidence-based risk panel and a prioritized improvement roadmap.

Presentation only — all reasoning comes from the agent via the AI Platform. The
dashboard repeatedly stresses that these are **resume-quality** signals, never a
hiring ranking.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.ai.agents.resume.agent import ResumeAnalystInput, resume_analyst_agent
from src.ai.agents.resume.schemas import ResumeAnalysis
from src.ai.core.runner import AgentRunner

_runner: AgentRunner | None = None

_PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟡 Low"}
_RISK_BADGE = {"high": "🔴", "medium": "🟠", "low": "🟡"}
_LEVEL_COLOR = {
    "Low": "🟢",
    "Low-Medium": "🟢",
    "Medium": "🟡",
    "High": "🔴",
}


def _get_runner() -> AgentRunner:
    """Return a shared runner (offline/local defaults are fine for the UI)."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


def render_resume_intelligence(
    candidate: Any,
    *,
    jd: str = "",
    key_prefix: str = "ri",
) -> None:
    """Render the Resume Intelligence dashboard for one candidate.

    Args:
        candidate: The candidate whose resume to analyze.
        jd: Optional JD text (ATS keyword coverage only — never ranking).
        key_prefix: Unique Streamlit widget-key prefix.
    """
    candidate_id = getattr(candidate, "candidate_id", "resume")
    st.subheader("📄 Resume Intelligence")
    st.caption(
        "Recruiter-grade resume quality analysis — structure, writing, ATS, "
        "projects, achievements and evidence-based risks. **Resume quality only; "
        "this never affects hiring ranking.**"
    )

    runner = _get_runner()
    payload = ResumeAnalystInput(candidate_id=candidate_id, candidate=candidate, jd=jd)

    result = runner.peek(resume_analyst_agent, payload)
    cols = st.columns([1, 1, 4])
    generate = cols[0].button("✨ Analyze", key=f"{key_prefix}_gen_{candidate_id}")
    refresh = cols[1].button(
        "♻ Refresh", key=f"{key_prefix}_ref_{candidate_id}", disabled=result is None
    )
    if generate or refresh or result is None:
        with st.spinner("Analyzing resume…"):
            result = runner.run(resume_analyst_agent, payload)

    if result is None or not result.ok or result.data is None:
        st.error(f"Resume analysis unavailable: {getattr(result, 'error', 'unknown')}")
        return

    st.caption(
        f"provider: {result.provider} · {'💾 cached' if result.cache_hit else '🟢 generated'} "
        f"· {result.latency_ms:.0f} ms"
    )
    for warning in result.warnings:
        st.caption(f"⚠ {warning}")

    _render_dashboard(result.data, key_prefix)


def _render_dashboard(analysis: ResumeAnalysis, key_prefix: str) -> None:
    """Render the full dashboard from a validated :class:`ResumeAnalysis`."""
    q = analysis.resume_quality

    # -- headline row -------------------------------------------------------
    top = st.columns(4)
    top[0].metric("Overall Resume Quality", f"{q.overall:.0f}/100")
    top[1].metric("ATS", analysis.ats_report.friendliness or "—")
    level = analysis.risk_report.level
    top[2].metric("Resume Risk", f"{_LEVEL_COLOR.get(level, '⚪')} {level}")
    top[3].metric("Career Direction", analysis.career_story.direction or "—")

    st.info(analysis.executive_summary)

    # -- quality dimensions -------------------------------------------------
    st.markdown("#### 📊 Quality Dimensions")
    dims = {
        "Structure": q.structure,
        "Writing": q.writing,
        "Technical Depth": q.technical_depth,
        "Project Quality": q.project_quality,
        "Achievements": q.achievements,
        "ATS Friendliness": q.ats_friendliness,
        "Professionalism": q.professionalism,
        "Career Narrative": q.career_narrative,
    }
    bar_cols = st.columns(2)
    for i, (name, value) in enumerate(dims.items()):
        with bar_cols[i % 2]:
            st.caption(f"{name} — {value:.0f}/100")
            st.progress(min(1.0, max(0.0, value / 100.0)))
    try:
        st.bar_chart(dims)
    except Exception:
        pass

    # -- strengths / weaknesses --------------------------------------------
    sw = st.columns(2)
    with sw[0]:
        st.markdown("#### ✅ Strengths")
        _bullets(analysis.strengths, "None surfaced.")
    with sw[1]:
        st.markdown("#### ⚠️ Weaknesses")
        _bullets(analysis.weaknesses, "None surfaced.")

    # -- detailed tabs ------------------------------------------------------
    tabs = st.tabs(
        [
            "🧭 Career",
            "✍️ Writing",
            "🧪 Technical",
            "📦 Projects",
            "🏆 Achievements",
            "🔎 ATS",
            "🚨 Risk",
            "🗺️ Roadmap",
        ]
    )

    with tabs[0]:
        cs = analysis.career_story
        st.write(cs.narrative)
        meta = st.columns(4)
        meta[0].metric("Direction", cs.direction or "—")
        meta[1].metric("Growth", cs.growth or "—")
        meta[2].metric("Consistency", cs.consistency or "—")
        meta[3].metric("Focus", cs.focus or "—")
        _bullets(cs.observations, "No observations.")

    with tabs[1]:
        w = analysis.writing
        wm = st.columns(4)
        wm[0].metric("Tone", w.tone or "—")
        wm[1].metric("Clarity", w.clarity or "—")
        wm[2].metric("Action Verbs", w.action_verb_usage or "—")
        wm[3].metric("Bullets", w.bullet_quality or "—")
        _bullets(w.observations, "No observations.")
        if w.sample_rewrites:
            st.markdown("**Suggested rewrites**")
            for rw in w.sample_rewrites:
                with st.expander(rw.before[:70] or "Rewrite"):
                    st.markdown(f"**Before:** {rw.before}")
                    st.markdown(f"**After:** {rw.after}")
                    st.caption(rw.reason)

    with tabs[2]:
        t = analysis.technical
        chips = st.columns(4)
        chips[0].metric("Cloud", "Yes" if t.cloud_exposure else "No")
        chips[1].metric("AI/ML", "Yes" if t.ai_exposure else "No")
        chips[2].metric("Production", "Yes" if t.production_exposure else "No")
        chips[3].metric("Open Source", "Yes" if t.open_source else "No")
        st.caption("Diversity: " + (t.diversity or "—") + " · Depth: " + (t.depth or "—"))
        if t.modern_technologies:
            st.markdown("**Modern:** " + ", ".join(t.modern_technologies))
        if t.dated_technologies:
            st.markdown("**Dated:** " + ", ".join(t.dated_technologies))
        _bullets(t.observations, "No observations.")

    with tabs[3]:
        if not analysis.projects:
            st.caption("No distinct projects detected in the resume.")
        for proj in analysis.projects:
            with st.expander(f"{proj.name} — {proj.complexity} complexity"):
                pm = st.columns(3)
                pm[0].metric("Impact", proj.impact or "—")
                pm[1].metric("Production", proj.production_readiness or "—")
                pm[2].metric("Uniqueness", proj.uniqueness or "—")
                if proj.technologies:
                    st.caption("Tech: " + ", ".join(proj.technologies))
                st.caption("Evidence: " + proj.evidence)

    with tabs[4]:
        a = analysis.achievements
        st.metric("Achievement Strength", a.strength or "—")
        st.markdown("**Quantified**")
        _bullets(a.quantified, "No quantified achievements found.")
        st.markdown("**Leadership**")
        _bullets(a.leadership, "None found.")
        if a.missing:
            st.markdown("**Missing**")
            _bullets(a.missing, "")

    with tabs[5]:
        ats = analysis.ats_report
        st.metric("ATS Friendliness", ats.friendliness or "—")
        if ats.matched_keywords:
            st.markdown("**Matched keywords:** " + ", ".join(ats.matched_keywords))
        if ats.missing_keywords:
            st.markdown("**Missing keywords:** " + ", ".join(ats.missing_keywords))
        _bullets(ats.parsing_notes, "No parsing notes.")
        _bullets(ats.suggestions, "")

    with tabs[6]:
        st.markdown(f"**Overall resume risk: {_LEVEL_COLOR.get(level, '⚪')} {level}**")
        if not analysis.risk_report.findings:
            st.success("No evidence-based resume risks detected.")
        for finding in analysis.risk_report.findings:
            badge = _RISK_BADGE.get(finding.severity, "🟡")
            st.markdown(f"{badge} **{finding.type}** — {finding.issue}")
            st.caption("Evidence: " + finding.evidence)
        if analysis.risk_report.positive_signals:
            st.markdown("**Positive signals**")
            _bullets(analysis.risk_report.positive_signals, "")

    with tabs[7]:
        st.markdown("#### 🗺️ Improvement Roadmap (highest impact first)")
        if not analysis.improvement_plan:
            st.caption("No improvements suggested — the resume is in good shape.")
        for i, imp in enumerate(analysis.improvement_plan, start=1):
            badge = _PRIORITY_BADGE.get(imp.priority, imp.priority)
            with st.expander(f"{i}. {imp.title}  ·  {badge}  ·  {imp.area}"):
                st.write(imp.rationale)
                if imp.example:
                    st.caption("Example: " + imp.example)

    st.caption("📌 " + analysis.confidence_note)


def _bullets(items: list[str], empty_message: str) -> None:
    """Render a bullet list, or a caption when empty."""
    if not items:
        if empty_message:
            st.caption(empty_message)
        return
    for item in items:
        st.write("•", item)


# ---------------------------------------------------------------------------
# Standalone workspace (candidate picker → dashboard)
# ---------------------------------------------------------------------------

RepositoryFactory = Callable[[], Any]


def render_resume_workspace(repository_factory: RepositoryFactory, *, jd: str = "") -> None:
    """Render the Resume Intelligence workspace with a candidate picker."""
    st.title("📄 Resume Intelligence")
    st.caption(
        "Enterprise resume analysis powered by the ResumeAnalystAgent — an "
        "evidence-based recruiter + career coach. Resume quality only."
    )

    try:
        repository = repository_factory()
    except Exception as exc:  # data/index not ready
        st.error(f"Resume data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available to analyze.")
        return

    ids = [c.candidate_id for c in candidates]
    chosen = st.selectbox("Select a candidate", ids, key="ri_pick")
    jd_text = st.text_area(
        "Optional job description (ATS keyword coverage only)", value=jd, key="ri_jd"
    )

    candidate = repository.get(chosen)
    if candidate is not None:
        render_resume_intelligence(candidate, jd=jd_text, key_prefix="ri_ws")
