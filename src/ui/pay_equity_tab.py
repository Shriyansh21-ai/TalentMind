"""Enterprise Pay Equity Guardian workspace (Modules 9, 10, 11).

A professional fairness-governance workspace that renders the unified
:class:`PayEquityReport`: the equity-risk gauge, internal-equity findings,
compression matrix, inversion analysis, promotion equity, policy alignment, the
fairness assessment, the executive-review approval flow, scenario comparison and
a transparency dashboard.

Presentation only — all reasoning comes from :class:`PayEquityGuardianEngine`,
which reuses the Compensation Governance offer, fabricates no payroll and never
concludes a legal violation. When no HRIS data is connected, the workspace
clearly shows internal comparisons as unavailable.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

import streamlit as st

from src.ai.core.runner import AgentRunner
from src.ai.agents.pay_equity.equity_engine import PayEquityGuardianEngine
from src.ai.agents.pay_equity.schemas import PayEquityReport
from src.ai.agents.pay_equity.templates import PAY_POLICIES, get_policy

_runner: Optional[AgentRunner] = None
_engine: Optional[PayEquityGuardianEngine] = None


def _get_engine(insights_fn=None) -> PayEquityGuardianEngine:
    """Return a shared pay-equity engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = PayEquityGuardianEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_pay_equity(
    candidate: Any,
    *,
    jd: str = "",
    policy: str = "",
    insights_fn=None,
    generated_on: str = "",
    key_prefix: str = "pe",
) -> None:
    """Build the pay-equity report for a candidate and render the workspace."""
    st.subheader("⚖️ Enterprise Pay Equity Guardian")
    st.caption(
        "Internal fairness & governance intelligence. It reuses the Compensation "
        "Governance offer and asks: is this offer internally fair, will it create "
        "compression or promotion inequity, does it align with pay policy, and who "
        "should review it. It surfaces governance risks only — never a legal "
        "conclusion, never a discrimination finding, and no payroll is fabricated."
    )

    with st.spinner("Evaluating internal pay equity…"):
        engine = _get_engine(insights_fn)
        report = engine.build(candidate=candidate, jd=jd, policy=policy, generated_on=generated_on)

    _render_report(report, key_prefix=key_prefix)


def _render_report(report: PayEquityReport, *, key_prefix: str) -> None:
    """Render a full :class:`PayEquityReport`."""
    narrative = report.narrative

    top = st.columns(5)
    top[0].metric("Equity Risk", report.equity_risk.level)
    top[1].metric("Compression", report.compression.risk_level)
    top[2].metric("Inversion", report.inversion.risk_level)
    top[3].metric("Policy", report.policy_alignment.alignment)
    top[4].metric("Review", report.executive_review.review_level)

    if not report.data_available:
        st.info("ℹ️ No internal compensation data connected — internal comparisons are unavailable and findings are provisional (Module 14).")
    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "📄 Summary",
            "⚖️ Equity",
            "📉 Compression",
            "🔀 Inversion",
            "📈 Promotion",
            "📋 Policy",
            "🧭 Fairness",
            "✅ Approvals",
            "🎚️ Scenarios",
            "📊 Dashboard",
        ]
    )

    with tabs[0]:
        st.info(narrative.executive_summary)
        st.caption("🔎 " + narrative.data_availability_note)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Key findings**"); _bullets(narrative.key_findings, "")
        with c[1]:
            st.markdown("**Human-review recommendations**"); _bullets(narrative.human_review_recommendations, "")
        st.markdown("**Assumptions**"); _bullets(narrative.assumptions, "")
        st.caption("📌 " + narrative.confidence_note)

    with tabs[1]:
        er = report.equity_risk
        st.metric("Overall internal-equity risk", er.level)
        st.caption(f"Confidence {er.confidence:.0f}/100 · data available: {er.data_available}")
        st.markdown("**Risk drivers**"); _bullets(er.drivers, "")
        st.markdown("**Internal-equity findings (each explains WHY)**")
        for f in report.equity_findings:
            badge = {"Consistent": "✅", "Review": "⚠️", "Not Evaluable": "➖"}.get(f.status, "•")
            st.markdown(f"{badge} **{f.dimension}** — {f.status}  _({f.register})_")
            st.caption(f.rationale)

    with tabs[2]:
        cm = report.compression
        st.metric("Compression risk", cm.risk_level)
        st.write(cm.rationale)
        if cm.business_impact:
            st.markdown("**Business impact**"); st.write(cm.business_impact)
        if cm.mitigation:
            st.markdown("**Suggested mitigation**"); st.write(cm.mitigation)
        if cm.evidence:
            st.markdown("**Evidence**"); _bullets(cm.evidence, "")

    with tabs[3]:
        iv = report.inversion
        st.metric("Inversion risk", iv.risk_level)
        st.write(iv.rationale)
        if iv.cases:
            st.markdown("**Potential cases (peers anonymized)**")
            for case in iv.cases:
                st.caption(f"• {case.peer_ref}: {case.detail}")
        if iv.business_impact:
            st.caption("Business impact: " + iv.business_impact)
        if iv.recommended_review:
            st.caption("Recommended review: " + iv.recommended_review)

    with tabs[4]:
        pr = report.promotion
        st.metric("Promotion equity", pr.consistency)
        st.write(pr.level_alignment)
        st.write(pr.progression_note)
        st.markdown("**Recommendations**"); _bullets(pr.recommendations, "")
        st.caption(f"Confidence {pr.confidence:.0f}/100")

    with tabs[5]:
        pol = report.policy_alignment
        st.metric(f"Policy: {pol.policy_name}", pol.alignment)
        st.write(pol.rationale)
        if pol.violations:
            st.markdown("**Policy exceptions flagged for review**"); _bullets(pol.violations, "")
        st.markdown("**Review requirements**"); _bullets(pol.review_requirements, "")

    with tabs[6]:
        fa = report.fairness
        st.write(fa.assessment)
        st.markdown("**Potential concerns**"); _bullets(fa.concerns, "")
        st.markdown("**Human-review recommendations**"); _bullets(fa.human_review_recommendations, "")
        st.markdown("**Governance notes**"); _bullets(fa.governance_notes, "")
        if fa.evidence:
            st.markdown("**Evidence**"); _bullets(fa.evidence, "")
        st.markdown("**Assumptions**"); _bullets(fa.assumptions, "")

    with tabs[7]:
        er = report.executive_review
        st.metric("Review level", er.review_level)
        st.write(er.rationale)
        for a in er.approvals:
            badge = "✅ required" if a.required else "— not required"
            st.markdown(f"**{a.approver}** · {badge}")
            st.caption(a.reason)

    with tabs[8]:
        cols = st.columns(len(report.scenarios))
        for col, sc in zip(cols, report.scenarios):
            with col:
                st.markdown(f"### {sc.name}")
                st.metric("Target", f"{sc.offer_target:.1f} {sc.unit}")
                st.caption("Equity: " + sc.equity_impact)
                st.caption("Budget: " + sc.budget_impact)
                st.caption("Promotion: " + sc.promotion_impact)
                st.caption("Retention: " + sc.retention_impact)
                if sc.tradeoffs:
                    st.markdown("**Trade-offs**"); _bullets(sc.tradeoffs, "")

    with tabs[9]:
        _render_dashboard(report)


def _render_dashboard(report: PayEquityReport) -> None:
    """Render the enterprise pay-equity dashboard (Module 10)."""
    charts = report.charts
    gauge = charts.get("equity_risk_gauge", {})
    st.markdown("**Equity risk gauge**")
    st.caption(" · ".join(f"**{s}**" if s == gauge.get("level") else s for s in gauge.get("scale", [])))

    cm = charts.get("compression_matrix", {})
    st.markdown("**Compression / inversion matrix**")
    st.caption(f"Compression: {cm.get('compression', 'n/a')} · Inversion: {cm.get('inversion', 'n/a')}")

    st.markdown("**Approval flow**")
    for step in charts.get("approval_flow", []):
        mark = "✅" if step.get("required") else "—"
        st.caption(f"{mark} {step.get('approver')}")

    oa = charts.get("offer_alignment", {})
    st.markdown("**Offer alignment**")
    st.caption(f"Policy {oa.get('policy')}: {oa.get('alignment')} · target {oa.get('target')} {oa.get('unit')}")

    gs = charts.get("governance_status", {})
    st.markdown("**Governance status**")
    st.caption(f"Review level: {gs.get('review_level')} · required: {', '.join(gs.get('required_approvers', []))}")

    st.markdown("**Scenario comparison**")
    for name, v in charts.get("scenario_comparison", {}).items():
        st.caption(f"{name}: target {v.get('target')} — {v.get('equity_impact')}")

    st.markdown("**Executive review pipeline**")
    st.caption(" → ".join(charts.get("executive_review_pipeline", [])) or "Standard approvals")


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

RepositoryFactory = Callable[[], Any]


def render_pay_equity_workspace(repository_factory: RepositoryFactory, *, insights_fn=None) -> None:
    """Render the Pay Equity Guardian workspace (pick candidate + policy → run)."""
    st.title("⚖️ Enterprise Pay Equity Guardian")
    st.caption(
        "TalentMind's internal fairness & governance engine. It helps HR, Finance, "
        "Legal and Executives evaluate compensation fairness with transparent, "
        "evidence-backed reasoning — explicitly flagging unavailable data and "
        "avoiding unsupported legal conclusions."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Pay-equity data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available.")
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 2, 2])
    chosen = cols[0].selectbox("Candidate", ids, key="pe_pick")
    policy_keys = list(PAY_POLICIES)
    policy = cols[1].selectbox(
        "Company pay policy",
        policy_keys,
        format_func=lambda k: get_policy(k).name,
        key="pe_policy",
    )
    cols[2].caption(get_policy(policy).summary)
    jd_text = st.text_area("Optional job description (sharpens role alignment)", key="pe_jd")

    if st.button("⚖️ Run pay-equity review", type="primary", key="pe_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_pay_equity(candidate, jd=jd_text, policy=policy, insights_fn=insights_fn, key_prefix="pe_ws")
