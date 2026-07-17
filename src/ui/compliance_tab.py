"""Enterprise Hiring Compliance workspace (Modules 8, 10, 11).

A professional governance workspace that renders the unified
:class:`HiringComplianceReport`: workflow status, the approval matrix, policy
findings, documentation review, audit-trail readiness, governance risk,
structured exceptions, the Legal/Compliance review determination, scenario
simulations and an enterprise dashboard.

Presentation only — all reasoning comes from :class:`HiringComplianceEngine`,
which reuses the whole intelligence chain, gives no legal advice and fabricates no
compliance conclusion. Items needing an external system are shown as pending review.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.ai.agents.compliance.compliance_report import HiringComplianceEngine
from src.ai.agents.compliance.schemas import HiringComplianceReport
from src.ai.core.runner import AgentRunner
from src.ui.theme import level_pill, status_pill

_runner: AgentRunner | None = None
_engine: HiringComplianceEngine | None = None


def _get_engine(insights_fn=None) -> HiringComplianceEngine:
    """Return a shared compliance engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = HiringComplianceEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_compliance(
    candidate: Any,
    *,
    jd: str = "",
    insights_fn=None,
    generated_on: str = "",
    key_prefix: str = "cp",
) -> None:
    """Build the compliance report for a candidate and render the workspace."""
    st.subheader("Enterprise Hiring Compliance")
    st.caption(
        "Governance & compliance intelligence. It reuses the whole hiring "
        "intelligence chain and asks: does this workflow follow company "
        "governance, are approvals complete, are mandatory steps or documents "
        "missing, does it satisfy policy, and should Legal/Compliance review it. "
        "It supports compliance — it never provides legal advice or fabricates a conclusion."
    )

    with st.spinner("Evaluating hiring compliance…"):
        engine = _get_engine(insights_fn)
        report = engine.build(candidate=candidate, jd=jd, generated_on=generated_on)

    _render_report(report, key_prefix=key_prefix)


def _render_report(report: HiringComplianceReport, *, key_prefix: str) -> None:
    """Render a full :class:`HiringComplianceReport`."""
    narrative = report.narrative

    top = st.columns(5)
    top[0].metric("Workflow", report.workflow.status)
    top[1].metric("Steps", f"{report.workflow.completed}/{report.workflow.total}")
    top[2].metric("Governance Risk", report.governance_risk.level)
    top[3].metric("Audit", report.audit.status)
    top[4].metric("Review", ", ".join(report.review.reviewers) or "Standard")

    if not report.data_available:
        st.info(
            "No governance / workflow / document system connected — approvals and documents that need an external system are shown as pending review (Module 14)."
        )
    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "Summary",
            "Workflow",
            "Approvals",
            "Policy",
            "Documentation",
            "Audit",
            "Risk & Exceptions",
            "Review",
            "Scenarios",
            "Dashboard",
        ]
    )

    with tabs[0]:
        st.info(narrative.executive_summary)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Key findings**")
            _bullets(narrative.key_findings, "")
            st.markdown("**Required actions**")
            _bullets(narrative.required_actions, "")
        with c[1]:
            st.markdown("**Human-review recommendations**")
            _bullets(narrative.human_review_recommendations, "")
            st.markdown("**Assumptions**")
            _bullets(narrative.assumptions, "")
        st.caption(narrative.confidence_note)

    with tabs[1]:
        st.caption(narrative.workflow_note)
        for step in report.workflow.steps:
            st.markdown(
                f"{status_pill(step.status)} **{step.name}** _({step.register})_",
                unsafe_allow_html=True,
            )
            st.caption(step.rationale)

    with tabs[2]:
        st.caption(narrative.approval_note)
        for a in report.approvals.approvals:
            tag = "required" if a.required else "not required"
            st.markdown(
                f"{status_pill(a.state)} **{a.approver}** · {tag}",
                unsafe_allow_html=True,
            )
            st.caption(a.reason)

    with tabs[3]:
        st.caption(narrative.policy_note)
        for p in report.policy_checks:
            st.markdown(f"{status_pill(p.status)} **{p.policy_name}**", unsafe_allow_html=True)
            st.caption(p.rationale)
            if p.required_actions:
                _bullets(p.required_actions, "")

    with tabs[4]:
        st.caption(narrative.documentation_note)
        for d in report.documentation.documents:
            st.markdown(
                f"{status_pill(d.state)} **{d.name}** _({d.register})_",
                unsafe_allow_html=True,
            )
        missing = report.documentation.missing()
        if missing:
            st.error("Missing: " + ", ".join(missing))

    with tabs[5]:
        st.metric("Audit-trail readiness", report.audit.status)
        for f in report.audit.findings:
            st.markdown(f"{status_pill(f.status)} **{f.dimension}**", unsafe_allow_html=True)
            st.caption(f.rationale)

    with tabs[6]:
        gr = report.governance_risk
        st.metric("Governance risk", gr.level)
        st.markdown("**Drivers**")
        _bullets(gr.drivers, "")
        st.markdown("**Missing controls**")
        _bullets(gr.missing_controls, "None.")
        st.markdown("**Exceptions**")
        for e in report.exceptions:
            st.markdown(
                f"{level_pill(e.severity)} **[{e.severity}] {e.kind}**",
                unsafe_allow_html=True,
            )
            st.caption(e.detail + (f" → {e.recommendation}" if e.recommendation else ""))

    with tabs[7]:
        rv = report.review
        st.write(rv.rationale)
        c = st.columns(2)
        c[0].metric(
            "Legal review", "Recommended" if rv.legal_review_recommended else "Not required"
        )
        c[1].metric(
            "Compliance review",
            "Recommended" if rv.compliance_review_recommended else "Not required",
        )
        st.caption(
            "Requesting a review routes the matter to a person — it is not itself a legal opinion."
        )

    with tabs[8]:
        st.caption("Governance impact if a control were skipped (Module 9).")
        for sc in report.scenarios:
            with st.expander(f"[{sc.severity}] {sc.name}"):
                st.write(sc.governance_impact)
                if sc.affected_controls:
                    st.markdown("**Affected controls**")
                    _bullets(sc.affected_controls, "")

    with tabs[9]:
        _render_dashboard(report)


def _render_dashboard(report: HiringComplianceReport) -> None:
    """Render the enterprise compliance dashboard (Module 10)."""
    charts = report.charts
    cs = charts.get("compliance_status", {})
    cols = st.columns(3)
    cols[0].metric("Workflow", cs.get("workflow_status", "n/a"))
    cols[1].metric("Governance", cs.get("governance_risk", "n/a"))
    cols[2].metric("Audit", cs.get("audit_status", "n/a"))

    wc = charts.get("workflow_completion", {})
    st.markdown("**Workflow completion**")
    st.progress(max(0.0, min(1.0, wc.get("ratio", 0.0))))
    st.caption(f"{wc.get('completed', 0)}/{wc.get('total', 0)} steps completed")

    st.markdown("**Approval flow**")
    for step in charts.get("approval_flow", []):
        if step.get("required"):
            st.caption(f"{step.get('approver')} — {step.get('state')}")

    ar = charts.get("audit_readiness", {})
    st.markdown("**Audit readiness**")
    for dim, status in ar.get("findings", {}).items():
        st.caption(f"{dim}: {status}")

    gh = charts.get("governance_health", {})
    st.markdown("**Governance health**")
    st.caption(" · ".join(f"**{s}**" if s == gh.get("level") else s for s in gh.get("scale", [])))

    missing = charts.get("missing_documentation", [])
    st.markdown("**Missing documentation**")
    st.caption(", ".join(missing) if missing else "None missing.")


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


def render_compliance_workspace(repository_factory: RepositoryFactory, *, insights_fn=None) -> None:
    """Render the Hiring Compliance workspace (pick candidate → run)."""
    st.title("Enterprise Hiring Compliance")
    st.caption(
        "TalentMind's governance & compliance layer. It helps HR, Compliance, "
        "Legal, Finance and Executive teams understand whether a hiring process "
        "follows organizational policy and governance requirements — with "
        "transparent, evidence-backed reasoning and without providing legal advice."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Compliance data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available.")
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 3])
    chosen = cols[0].selectbox("Candidate", ids, key="cp_pick")
    jd_text = cols[1].text_area("Optional job description (sharpens role alignment)", key="cp_jd")

    if st.button("Run compliance review", type="primary", key="cp_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_compliance(candidate, jd=jd_text, insights_fn=insights_fn, key_prefix="cp_ws")
