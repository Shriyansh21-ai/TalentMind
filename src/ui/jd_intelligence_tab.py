"""JD Intelligence dashboard (Module 13).

A professional, enterprise UI over the :class:`JDAnalysis` produced by the
JDAnalystAgent — consistent with the Resume Intelligence workspace. It shows
quality dimensions (progress bars + chart), role intelligence, hiring-intent
visualization (confidence bars), a requirement hierarchy, a technology map, an
evidence-based risk panel and a prioritized improvement roadmap.

Presentation only — all reasoning comes from the agent via the AI Platform. The
dashboard repeatedly stresses these are **JD-quality** signals, never a candidate
ranking.
"""

from __future__ import annotations

from typing import List, Optional

import streamlit as st

from src.ai.core.runner import AgentRunner
from src.ai.agents.jd.agent import JDAnalystInput, jd_analyst_agent
from src.ai.agents.jd.schemas import JDAnalysis

_runner: Optional[AgentRunner] = None

_PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟡 Low"}
_RISK_BADGE = {"high": "🔴", "medium": "🟠", "low": "🟡"}
_LEVEL_COLOR = {"Low": "🟢", "Low-Medium": "🟢", "Medium": "🟡", "High": "🔴"}

_SAMPLE_JD = """Senior Machine Learning Engineer
Department: AI Platform
Location: Remote (US)
Employment Type: Full-time

About Us
We are a fast-paced Series B startup building a generative AI platform for enterprises.

What you'll do
- Design and own scalable ML systems in production serving millions of requests
- Lead and mentor a small team of engineers
- Partner with product and stakeholders across functions
- Drive the architecture and roadmap for our RAG platform

Requirements
- 8+ years of experience in software engineering
- Strong Python and experience with PyTorch and LLMs
- Must have experience with AWS, Kubernetes and distributed systems

Nice to have
- Experience with Rust
- Familiarity with Terraform and GraphQL

Benefits
- Equity, health insurance, unlimited PTO
"""


def _get_runner() -> AgentRunner:
    """Return a shared runner (offline/local defaults are fine for the UI)."""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


def render_jd_intelligence(jd_text: str, *, jd_id: str = "", key_prefix: str = "jdi") -> None:
    """Render the JD Intelligence dashboard for a given JD text."""
    st.subheader("🧾 JD Intelligence")
    st.caption(
        "Enterprise job-description analysis — role level, hiring intent, "
        "requirement hierarchy, market posture and evidence-based risks. "
        "**JD quality only; this never affects candidate ranking.**"
    )
    if not jd_text.strip():
        st.info("Paste a job description above and click **Analyze JD**.")
        return

    with st.spinner("Analyzing job description…"):
        result = _get_runner().run(jd_analyst_agent, JDAnalystInput(jd_text=jd_text, jd_id=jd_id))

    if not result.ok or result.data is None:
        st.error(f"JD analysis unavailable: {getattr(result, 'error', 'unknown')}")
        return

    st.caption(
        f"provider: {result.provider} · {'💾 cached' if result.cache_hit else '🟢 generated'} "
        f"· {result.latency_ms:.0f} ms"
    )
    for warning in result.warnings:
        st.caption(f"⚠ {warning}")

    _render_dashboard(result.data)


def _render_dashboard(a: JDAnalysis) -> None:
    """Render the full dashboard from a validated :class:`JDAnalysis`."""
    q = a.quality

    top = st.columns(4)
    top[0].metric("Overall JD Quality", f"{q.overall:.0f}/100")
    top[1].metric("Role", a.role_intelligence.seniority or "—")
    level = a.risk_report.level
    top[2].metric("JD Risk", f"{_LEVEL_COLOR.get(level, '⚪')} {level}")
    top[3].metric("Hiring Intent", a.hiring_intent.primary_intent or "—")

    st.info(a.executive_summary)

    # -- quality dimensions -------------------------------------------------
    st.markdown("#### 📊 JD Quality Dimensions")
    dims = {
        "Structure": q.structure,
        "Technical Clarity": q.technical_clarity,
        "Role Clarity": q.role_clarity,
        "Requirement Quality": q.requirement_quality,
        "Business Context": q.business_context,
        "Hiring Readiness": q.hiring_readiness,
        "Market Alignment": q.market_alignment,
        "Organization Clarity": q.organization_clarity,
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

    sw = st.columns(2)
    with sw[0]:
        st.markdown("#### ✅ Strengths")
        _bullets(a.strengths, "None surfaced.")
    with sw[1]:
        st.markdown("#### ⚠️ Weaknesses")
        _bullets(a.weaknesses, "None surfaced.")

    tabs = st.tabs(
        [
            "🧭 Role",
            "🎯 Hiring Intent",
            "🧱 Requirements",
            "🗺️ Technology",
            "🏢 Organization",
            "📈 Market",
            "🚨 Risk",
            "🛠️ Roadmap",
        ]
    )

    with tabs[0]:
        r = a.role_intelligence
        rm = st.columns(4)
        rm[0].metric("Seniority", r.seniority or "—")
        rm[1].metric("Technical Level", r.technical_level or "—")
        rm[2].metric("Ownership", r.ownership or "—")
        rm[3].metric("Confidence", f"{r.confidence:.0f}%")
        detail = st.columns(3)
        detail[0].caption(f"Leadership: {r.leadership_expectations}")
        detail[1].caption(f"Architecture: {r.architecture_responsibility}")
        detail[2].caption(f"Management: {r.management_expectations}")
        _bullets(r.observations, "No observations.")

    with tabs[1]:
        hi = a.hiring_intent
        st.markdown(f"**Primary intent: {hi.primary_intent}**  ·  {hi.confidence:.0f}% confidence")
        st.caption(hi.summary)
        for sig in hi.signals:
            st.caption(f"{sig.intent} — {sig.confidence:.0f}%")
            st.progress(min(1.0, max(0.0, sig.confidence / 100.0)))
            st.caption(sig.rationale)
        if hi.business_priorities:
            st.markdown("**Business priorities:** " + ", ".join(hi.business_priorities))

    with tabs[2]:
        rh = a.requirement_hierarchy
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Mandatory**")
            _bullets(rh.mandatory, "None explicit.")
            st.markdown("**Nice-to-have**")
            _bullets(rh.nice_to_have, "None.")
        with cols[1]:
            st.markdown("**Preferred**")
            _bullets(rh.preferred, "None.")
            st.markdown("**Hidden / implicit expectations** (inference)")
            _bullets(rh.hidden_expectations + rh.implicit_requirements, "None inferred.")

    with tabs[3]:
        ti = a.technical_intelligence
        st.caption(f"Maturity: {ti.technology_maturity} · Diversity: {ti.technology_diversity}")
        groups = {
            "Languages": ti.languages,
            "Frameworks": ti.frameworks,
            "Cloud": ti.cloud,
            "AI / ML": ti.ai_ml,
            "DevOps": ti.devops,
            "Data": ti.data,
            "Security": ti.security,
            "Infrastructure": ti.infrastructure,
            "Architecture": ti.architecture,
        }
        for label, items in groups.items():
            if items:
                st.markdown(f"**{label}:** " + ", ".join(items))
        _bullets(ti.observations, "")

    with tabs[4]:
        org = a.organization_intelligence
        om = st.columns(3)
        om[0].metric("Company Type", org.company_type or "—")
        om[1].metric("Tech Maturity", org.technology_maturity or "—")
        om[2].metric("Eng Maturity", org.engineering_maturity or "—")
        st.caption(f"Confidence: {org.confidence:.0f}%")
        _bullets(org.signals, "No explicit signals.")
        _bullets(org.observations, "")

    with tabs[5]:
        mi = a.market_intelligence
        st.caption(mi.summary)
        for est in mi.estimates:
            st.markdown(f"**{est.dimension.replace('_', ' ').title()}** — {est.assessment}  ·  {est.confidence:.0f}% confidence")

    with tabs[6]:
        st.markdown(f"**Overall JD risk: {_LEVEL_COLOR.get(level, '⚪')} {level}**")
        if not a.risk_report.findings:
            st.success("No evidence-based JD risks detected.")
        for finding in a.risk_report.findings:
            badge = _RISK_BADGE.get(finding.severity, "🟡")
            st.markdown(f"{badge} **{finding.type}** — {finding.issue}")
            st.caption("Evidence: " + finding.evidence)
        if a.risk_report.positive_signals:
            st.markdown("**Positive signals**")
            _bullets(a.risk_report.positive_signals, "")

    with tabs[7]:
        st.markdown("#### 🛠️ Improvement Roadmap (highest impact first)")
        if not a.improvement_plan:
            st.caption("No improvements suggested — the JD is in good shape.")
        for i, imp in enumerate(a.improvement_plan, start=1):
            badge = _PRIORITY_BADGE.get(imp.priority, imp.priority)
            with st.expander(f"{i}. {imp.title}  ·  {badge}  ·  {imp.area}"):
                st.write(imp.rationale)
                if imp.example:
                    st.caption("Example: " + imp.example)

    st.caption("📌 " + a.confidence_note)


def _bullets(items: List[str], empty_message: str) -> None:
    """Render a bullet list, or a caption when empty."""
    if not items:
        if empty_message:
            st.caption(empty_message)
        return
    for item in items:
        st.write("•", item)


# ---------------------------------------------------------------------------
# Standalone workspace
# ---------------------------------------------------------------------------


def render_jd_workspace(*, jd: str = "") -> None:
    """Render the JD Intelligence workspace (paste a JD → dashboard)."""
    st.title("🧾 JD Intelligence")
    st.caption(
        "Enterprise job-description intelligence powered by the JDAnalystAgent — "
        "an evidence-based recruiter + hiring manager + org designer. JD quality only."
    )

    if st.button("📋 Load sample JD", key="jd_sample"):
        st.session_state["jd_text_input"] = _SAMPLE_JD

    jd_text = st.text_area(
        "Job description",
        value=st.session_state.get("jd_text_input", jd),
        height=300,
        key="jd_text_input",
    )
    analyze = st.button("✨ Analyze JD", type="primary", key="jd_analyze")

    if analyze or st.session_state.get("jd_analyzed"):
        st.session_state["jd_analyzed"] = True
        render_jd_intelligence(jd_text, key_prefix="jd_ws")
