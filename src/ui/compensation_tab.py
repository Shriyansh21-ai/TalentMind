"""Enterprise Compensation Governance workspace (Modules 10, 11, 12, 13).

A professional compensation-governance workspace that renders the unified
:class:`CompensationReport`: the recommended salary range, offer justification,
governance checks, market position, offer scenarios, negotiation strategy, budget
assessment, internal-equity readiness, future outlook, an enterprise dashboard
and — the flagship — the exportable transparency audit trail.

Presentation only — all reasoning comes from :class:`CompensationGovernanceEngine`,
which consumes existing structured outputs, fabricates no salary/market data and
never re-ranks.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.ai.agents.compensation.governance import CompensationGovernanceEngine
from src.ai.agents.compensation.schemas import CompensationReport
from src.ai.core.runner import AgentRunner

_runner: AgentRunner | None = None
_engine: CompensationGovernanceEngine | None = None


def _get_engine(insights_fn=None) -> CompensationGovernanceEngine:
    """Return a shared compensation engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = CompensationGovernanceEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_compensation(
    candidate: Any,
    *,
    jd: str = "",
    insights_fn=None,
    generated_on: str = "",
    key_prefix: str = "cg",
) -> None:
    """Build the compensation governance report for a candidate and render it."""
    st.subheader("Enterprise Compensation Governance")
    st.caption(
        "Not a salary predictor — a transparency system. It explains, justifies, "
        "documents and governs a compensation recommendation using evidence from "
        "TalentMind's existing intelligence, so HR, Finance, Legal and executives "
        "can confidently approve it. No salary survey, payroll or market data is fabricated."
    )

    with st.spinner("Building the compensation governance report…"):
        engine = _get_engine(insights_fn)
        report = engine.build(candidate=candidate, jd=jd, generated_on=generated_on)

    _render_report(report, key_prefix=key_prefix)


def _render_report(report: CompensationReport, *, key_prefix: str) -> None:
    """Render a full :class:`CompensationReport`."""
    band = report.recommended_range
    narrative = report.narrative

    top = st.columns(5)
    top[0].metric("Recommended Target", f"{band.currency} {band.target:.1f} {band.unit}")
    top[1].metric("Range", f"{band.minimum:.1f}–{band.maximum:.1f}")
    top[2].metric("Market Position", report.market_position.position)
    top[3].metric("Confidence", band.confidence_label)
    top[4].metric("Hire Type", report.budget.hire_type)

    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "Summary",
            "Recommendation",
            "Justification",
            "Governance",
            "Market",
            "Scenarios",
            "Negotiation",
            "Budget",
            "Internal Equity",
            "Future",
            "Dashboard",
            "Audit Trail",
        ]
    )

    with tabs[0]:
        st.info(narrative.executive_summary)
        st.markdown("**Recommendation rationale**")
        st.write(narrative.recommendation_rationale)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Key justifications**")
            _bullets(narrative.key_justifications, "")
        with c[1]:
            st.markdown("**Key assumptions**")
            _bullets(narrative.key_assumptions, "None flagged.")
        st.caption("" + narrative.confidence_note)
        st.caption("" + narrative.transparency_note)

    with tabs[1]:
        st.success(f"Recommended range: **{band.formatted()}**")
        cols = st.columns(3)
        cols[0].metric("Minimum", f"{band.minimum:.1f}")
        cols[1].metric("Target", f"{band.target:.1f}")
        cols[2].metric("Maximum", f"{band.maximum:.1f}")
        st.caption(
            f"Currency/unit: {band.currency} {band.unit} · confidence {band.confidence:.0f}/100 ({band.confidence_label})"
        )
        st.markdown("**Basis (evidence & reasoning)**")
        _bullets(band.basis, "")
        st.markdown("**Assumptions**")
        _bullets(band.assumptions, "")
        st.caption("This is a defensible range — never a single fixed salary (Module 1).")

    with tabs[2]:
        st.caption(
            "Every line is tagged Evidence / Reasoning / Business Impact / Assumption and cites its source."
        )
        for entry in report.justification:
            st.markdown(f"**{entry.kind}** — {entry.statement}")
            st.caption(
                f"Source: {entry.source}"
                + (f" · confidence {entry.confidence:.0f}" if entry.confidence else "")
            )

    with tabs[3]:
        st.caption("Every governance conclusion explains WHY (Module 3).")
        for check in report.governance_checks:
            st.markdown(f"**{check.dimension}** — {check.status}")
            st.caption(check.rationale + f" · {check.source}")

    with tabs[4]:
        mp = report.market_position
        st.metric("Market Position", mp.position)
        st.info(mp.data_note)
        st.write(mp.rationale)
        if mp.basis:
            st.markdown("**Basis**")
            _bullets(mp.basis, "")
        st.markdown("**Assumptions**")
        _bullets(mp.assumptions, "")

    with tabs[5]:
        cols = st.columns(len(report.scenarios))
        for col, sc in zip(cols, report.scenarios):
            with col:
                st.markdown(f"### {sc.name}")
                st.metric("Target", f"{sc.comp_range.target:.1f}")
                st.caption(sc.comp_range.formatted())
                st.markdown("**Advantages**")
                _bullets(sc.advantages, "")
                st.markdown("**Risks**")
                _bullets(sc.risks, "")
                st.caption("Negotiation: " + sc.negotiation_impact)
                st.caption("Retention: " + sc.retention_impact)
                st.caption("Business: " + sc.business_impact)

    with tabs[6]:
        ng = report.negotiation
        c = st.columns(3)
        c[0].metric("Acceptance", ng.acceptance_likelihood)
        c[1].metric("Negotiation Prob.", ng.negotiation_probability)
        c[2].metric("Confidence", f"{ng.confidence:.0f}/100")
        st.markdown("**Observed evidence**")
        _bullets(ng.observed_evidence, "")
        st.markdown("**Likely objections**")
        _bullets(ng.likely_objections, "")
        st.markdown("**Strategy**")
        _bullets(ng.strategy, "")
        st.markdown("**Fallback strategy**")
        _bullets(ng.fallback_strategy, "")
        st.markdown("**Executive approval notes**")
        _bullets(ng.executive_approval_notes, "")
        st.markdown("**Recruiter talking points**")
        _bullets(ng.recruiter_talking_points, "")

    with tabs[7]:
        bg = report.budget
        c = st.columns(3)
        c[0].metric("Hire Type", bg.hire_type)
        c[1].metric("Priority", bg.hiring_priority)
        c[2].metric("Utilization", bg.budget_utilization)
        st.write(bg.investment_rationale)
        st.write(bg.business_justification)
        st.markdown("**Assumptions**")
        _bullets(bg.assumptions, "")
        st.caption(
            f"Confidence {bg.confidence:.0f}/100. Financial figures are qualitative estimates, not connected metrics."
        )

    with tabs[8]:
        eq = report.internal_equity
        if not eq.available:
            st.info(f"{eq.status_message}")
            st.caption(
                "No payroll/HRIS source is connected. TalentMind ships no payroll connector (Module 8)."
            )
        else:
            st.success(eq.status_message)
            for check in eq.checks:
                st.markdown(f"- **{check.dimension}** ({check.status}): {check.rationale}")
        st.markdown("**Recommendations**")
        _bullets(eq.recommendations, "")
        st.markdown("**HRIS interfaces ready (future integration — Module 14)**")
        st.caption(", ".join(eq.hris_interfaces_ready))

    with tabs[9]:
        st.caption("Confidence is attached to every future estimate (Module 9).")
        for name, est in report.future_outlook.items():
            st.markdown(f"**{name}** — {est.level} ({est.kind}, confidence {est.confidence:.0f}%)")
            st.progress(max(0.0, min(1.0, est.confidence / 100.0)))
            if est.rationale:
                st.caption("• " + est.rationale)

    with tabs[10]:
        _render_dashboard(report)

    with tabs[11]:
        _render_audit_trail(report, key_prefix=key_prefix)


def _render_dashboard(report: CompensationReport) -> None:
    """Render the enterprise compensation dashboard (Module 11)."""
    charts = report.charts
    rr = charts.get("recommended_range", {})
    st.markdown("**Recommended salary range**")
    st.caption(
        f"{rr.get('currency', 'INR')} {rr.get('minimum', 0):.1f} — target {rr.get('target', 0):.1f} — {rr.get('maximum', 0):.1f} {rr.get('unit', 'LPA')}"
    )

    st.markdown("**Scenario comparison (target by scenario)**")
    _bar({name: v.get("target", 0) for name, v in charts.get("scenario_comparison", {}).items()})

    mp = charts.get("market_position", {})
    st.markdown("**Market position**")
    st.caption(
        " · ".join(f"**{p}**" if p == mp.get("position") else p for p in mp.get("scale", []))
    )

    ba = charts.get("budget_allocation", {})
    cols = st.columns(3)
    cols[0].metric("Hire Type", ba.get("hire_type", "n/a"))
    cols[1].metric("Priority", ba.get("priority", "n/a"))
    cols[2].metric("Offer Confidence", f"{charts.get('offer_confidence', 0):.0f}/100")

    nr = charts.get("negotiation_readiness", {})
    st.markdown("**Negotiation readiness**")
    st.progress(max(0.0, min(1.0, nr.get("acceptance_score", 0.0))))
    st.caption(
        f"Acceptance {nr.get('acceptance_likelihood', 'n/a')} · negotiation probability {nr.get('negotiation_probability', 'n/a')}"
    )

    st.markdown("**Business value overview**")
    for name, level in charts.get("business_value", {}).items():
        st.caption(f"{name}: {level}")


def _render_audit_trail(report: CompensationReport, *, key_prefix: str) -> None:
    """Render + export the flagship transparency audit trail (Module 12)."""
    audit = report.audit_trail
    st.markdown("### Transparency Audit Trail")
    c = st.columns(3)
    c[0].metric("Decision ID", audit.decision_id)
    c[1].metric("Confidence", f"{audit.confidence:.0f}/100")
    c[2].metric("Human Review", audit.human_review_status)
    st.caption(f"Timestamp: {audit.decision_timestamp or 'n/a'}")

    st.markdown("**Evidence sources**")
    _bullets(audit.evidence_sources, "")
    st.markdown("**AI agents consulted**")
    _bullets(audit.agents_consulted, "")
    st.markdown("**Reasoning chain**")
    for i, step in enumerate(audit.reasoning_chain, start=1):
        st.write(f"{i}. {step}")
    st.markdown("**Approvals required**")
    _bullets(audit.approvals_required, "")
    st.markdown("**Business justification**")
    st.write(audit.business_justification)

    export_text = audit.to_export_text()
    st.download_button(
        "Export audit trail (.txt)",
        data=export_text.encode("utf-8"),
        file_name=f"{audit.decision_id}_audit.txt",
        mime="text/plain",
        key=f"{key_prefix}_audit_dl_{report.report_id}",
    )
    import json

    st.download_button(
        "Export full report (.json)",
        data=json.dumps(report.to_dict(), indent=2).encode("utf-8"),
        file_name=f"{report.report_id}.json",
        mime="application/json",
        key=f"{key_prefix}_json_dl_{report.report_id}",
    )
    with st.expander("Preview audit-trail export"):
        st.code(export_text)


def _bar(data: dict) -> None:
    """Render a simple horizontal bar view for a ``{label: number}`` mapping."""
    if not data:
        st.caption("No data.")
        return
    peak = max([v for v in data.values() if isinstance(v, (int, float))] or [1]) or 1
    for label, value in data.items():
        if not isinstance(value, (int, float)):
            continue
        st.caption(f"{label}: {'▇' * int(round(value / peak * 12)) or '·'} {value:.1f}")


def _bullets(items: list[str], empty_message: str) -> None:
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


def render_compensation_workspace(
    repository_factory: RepositoryFactory, *, insights_fn=None
) -> None:
    """Render the Compensation Governance workspace (pick candidate → run)."""
    st.title("Enterprise Compensation Governance")
    st.caption(
        "TalentMind's compensation transparency system — it explains, justifies, "
        "documents and governs every compensation recommendation using evidence "
        "from the existing AI ecosystem. Its purpose is not to predict salaries "
        "but to make compensation decisions transparent, auditable and defensible."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Compensation data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available.")
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 3])
    chosen = cols[0].selectbox("Candidate", ids, key="cg_pick")
    jd_text = cols[1].text_area(
        "Optional job description (sharpens role alignment + governance)", key="cg_jd"
    )

    if st.button("Generate compensation governance report", type="primary", key="cg_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_compensation(candidate, jd=jd_text, insights_fn=insights_fn, key_prefix="cg_ws")
