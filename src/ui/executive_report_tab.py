"""Executive Hiring Report workspace (Modules 10, 11, 13, 14).

An enterprise workspace that renders the unified :class:`ExecutiveHiringReport` as
a boardroom briefing: a branded headline, a template selector, professional
visual dashboards, every section (executive summary, candidate/role intelligence,
committee decision, risk dashboard, interview strategy, action plan, business
intelligence, provenance) and one-click PDF / DOCX / HTML / PPTX + named-packet
downloads.

Presentation only — all reasoning comes from :class:`ExecutiveReportBuilder`,
which consumes existing structured outputs and never re-ranks or fabricates.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

import streamlit as st

from src.ai.core.runner import AgentRunner
from src.ai.agents.executive_report import charts as charts_mod
from src.ai.agents.executive_report.builder import ExecutiveReportBuilder
from src.ai.agents.executive_report.export import (
    FORMATS,
    PACKETS,
    export_report,
    mime_for,
    suffix_for,
)
from src.ai.agents.executive_report.schemas import ExecutiveHiringReport
from src.ai.agents.executive_report.templates import TEMPLATES, get_template

_runner: Optional[AgentRunner] = None
_builder: Optional[ExecutiveReportBuilder] = None


def _get_builder(insights_fn=None) -> ExecutiveReportBuilder:
    """Return a shared report builder (offline/local defaults)."""
    global _runner, _builder
    if _runner is None:
        _runner = AgentRunner()
    if _builder is None or insights_fn is not None:
        _builder = ExecutiveReportBuilder(insights_fn=insights_fn, ai_runner=_runner)
    return _builder


def render_executive_report(
    candidate: Any,
    *,
    jd: str = "",
    template: str = "executive",
    insights_fn=None,
    key_prefix: str = "er",
) -> None:
    """Build the executive report for a candidate and render the full workspace."""
    st.subheader("📊 Executive Hiring Report")
    st.caption(
        "A McKinsey-grade executive briefing that synthesizes every existing "
        "TalentMind intelligence source — committee, resume, JD, candidate "
        "intelligence, timeline, risk, interview and recommendation — into one "
        "evidence-backed report. No engine is re-run; nothing is fabricated."
    )

    with st.spinner("Synthesizing the executive report…"):
        builder = _get_builder(insights_fn)
        report = builder.build(candidate=candidate, jd=jd, template=template)

    _render_report(report, template=template, key_prefix=key_prefix)


def _render_report(report: ExecutiveHiringReport, *, template: str, key_prefix: str) -> None:
    """Render a full :class:`ExecutiveHiringReport`."""
    narrative = report.narrative

    top = st.columns(4)
    top[0].metric("Recommendation", narrative.overall_recommendation)
    top[1].metric("Executive Confidence", narrative.executive_confidence or "n/a")
    top[2].metric("Action", report.action_plan.primary_action)
    top[3].metric("Evidence Sources", len(report.evidence_sources))

    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "📄 Executive Summary",
            "👤 Candidate",
            "🧭 Role",
            "🏛️ Committee",
            "⚠️ Risk",
            "🎯 Interview",
            "✅ Action Plan",
            "💼 Business",
            "📈 Visuals",
            "⬇️ Export",
        ]
    )

    with tabs[0]:
        st.info(narrative.executive_summary)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Business impact**"); st.write(narrative.business_impact)
            st.markdown("**Technical impact**"); st.write(narrative.technical_impact)
            st.markdown("**Leadership potential**"); st.write(narrative.leadership_potential)
        with c[1]:
            st.markdown("**Risk overview**"); st.write(narrative.risk_overview)
            st.markdown("**Interview readiness**"); st.write(narrative.interview_readiness)
        c2 = st.columns(2)
        with c2[0]:
            st.markdown("**Top reasons**"); _bullets(narrative.top_reasons, "Not substantiated by the evidence.")
        with c2[1]:
            st.markdown("**Top concerns**"); _bullets(narrative.top_concerns, "None surfaced.")
        st.caption("📌 " + narrative.confidence_note)

    with tabs[1]:
        ci = report.candidate_intelligence
        charts_mod.render_scorecard(st, report.charts)
        story = report.candidate_overview.get("career_story")
        if story:
            st.markdown("**Career trajectory**"); st.write(story)
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Strengths**"); _bullets(ci.get("strengths", []), "None recorded.")
        with cols[1]:
            st.markdown("**Development areas**"); _bullets(ci.get("weaknesses", []), "None recorded.")

    with tabs[2]:
        ri = report.role_intelligence
        st.write(report.jd_summary)
        rows = {
            "Seniority": ri.get("seniority"),
            "Technical Level": ri.get("technical_level"),
            "Primary Hiring Intent": ri.get("primary_intent"),
            "Organization Maturity": ri.get("organization_maturity"),
            "Role Clarity": ri.get("role_clarity"),
        }
        for label, value in rows.items():
            if value:
                st.caption(f"**{label}:** {value}")
        if ri.get("mandatory"):
            st.markdown("**Mandatory requirements**"); _bullets(ri["mandatory"], "")
        if ri.get("technology_stack"):
            st.markdown("**Technology stack**"); _bullets(ri["technology_stack"], "")

    with tabs[3]:
        committee = report.committee
        if not committee:
            st.info("The AI Hiring Committee was not convened for this report.")
        else:
            consensus = committee.get("consensus", {})
            decision = committee.get("decision", {})
            cc = st.columns(3)
            cc[0].metric("Committee", str(consensus.get("recommendation", "n/a")))
            cc[1].metric("Consensus", str(consensus.get("level", "n/a")))
            cc[2].metric("Confidence", f"{committee.get('confidence', {}).get('overall', 0):.0f}/100")
            charts_mod.render_consensus_meter(st, report.charts)
            st.markdown("**Committee chair summary**"); st.write(decision.get("executive_summary", ""))
            st.markdown("**Every opinion**")
            _bullets(
                [
                    f"{o.get('role_title', o.get('role'))}: {o.get('recommendation')} "
                    f"(confidence {o.get('confidence', 0):.0f}%)"
                    for o in committee.get("opinions", [])
                ],
                "No opinions recorded.",
            )
            if committee.get("conflicts"):
                st.markdown("**Conflict resolution**")
                _bullets(
                    [
                        f"{c.get('member_a')} vs {c.get('member_b')} → {c.get('resolution_strategy', '')}"
                        for c in committee["conflicts"]
                    ],
                    "",
                )

    with tabs[4]:
        rd = report.risk_dashboard
        rc = st.columns(3)
        rc[0].metric("Overall Risk", str(rd.get("risk_level", "Unknown")))
        rc[1].metric("Risk Score", f"{rd.get('risk_score', 0):.0f}/100")
        rc[2].metric("Consistency", f"{rd.get('career_consistency', 0):.0f}/100")
        charts_mod.render_risk_matrix(st, report.charts)
        if rd.get("red_flags"):
            st.markdown("**Red flags**"); _bullets(rd["red_flags"], "")
        if rd.get("validation_questions"):
            st.markdown("**Mitigations — validate in interview**"); _bullets(rd["validation_questions"], "")

    with tabs[5]:
        iv = report.interview_strategy
        charts_mod.render_interview_roadmap(st, report.charts)
        st.markdown("**Roadmap**"); _bullets(iv.roadmap, "")
        for title, items in [
            ("Technical", iv.technical_interview),
            ("System Design", iv.system_design),
            ("Behavioral", iv.behavioral_interview),
            ("Leadership", iv.leadership_interview),
            ("Coding", iv.coding_interview),
            ("Evaluation Rubric", iv.evaluation_rubric),
            ("Decision Checkpoints", iv.decision_checkpoints),
        ]:
            if items:
                st.markdown(f"**{title}**"); _bullets(items, "")
        if iv.post_interview_recommendation:
            st.caption("📌 " + iv.post_interview_recommendation)

    with tabs[6]:
        ap = report.action_plan
        st.success(f"Recommended action: **{ap.primary_action}**")
        st.write(ap.rationale)
        if ap.alternatives:
            st.markdown("**Alternative dispositions**"); _bullets(ap.alternatives, "")
        st.markdown("**Expected onboarding plan**"); _bullets(ap.onboarding_plan, "")
        cols = st.columns(3)
        with cols[0]:
            st.markdown("**First 30 days**"); _bullets(ap.plan_30_day, "")
        with cols[1]:
            st.markdown("**First 60 days**"); _bullets(ap.plan_60_day, "")
        with cols[2]:
            st.markdown("**First 90 days**"); _bullets(ap.plan_90_day, "")

    with tabs[7]:
        st.caption("Confidence is attached to every estimate. Estimates restate existing intelligence.")
        for name, est in report.business_intelligence.items():
            st.caption(f"**{name}** — {est.level} (confidence {est.confidence:.0f}%)")
            st.progress(max(0.0, min(1.0, est.confidence / 100.0)))
            if est.rationale:
                st.caption("• " + est.rationale)

    with tabs[8]:
        charts_mod.render_all(st, report.charts)

    with tabs[9]:
        _render_export(report, template=template, key_prefix=key_prefix)


def _render_export(report: ExecutiveHiringReport, *, template: str, key_prefix: str) -> None:
    """Render the export controls (formats + named packets)."""
    st.markdown("**Download this report**")
    cols = st.columns(len(FORMATS))
    for col, fmt in zip(cols, FORMATS):
        try:
            data = export_report(report, fmt, template)
            col.download_button(
                f"{fmt.upper()}",
                data=data,
                file_name=f"{report.candidate_id}_{template}.{suffix_for(fmt)}",
                mime=mime_for(fmt),
                key=f"{key_prefix}_dl_{fmt}_{report.report_id}",
            )
        except Exception as exc:  # pragma: no cover - defensive
            col.caption(f"{fmt.upper()} unavailable: {exc}")

    st.markdown("**Named executive packets**")
    for pk_key, packet in PACKETS.items():
        try:
            data = export_report(report, packet.default_format, packet.template)
            st.download_button(
                f"📦 {packet.name} ({packet.default_format.upper()})",
                data=data,
                file_name=f"{report.candidate_id}_{pk_key}.{suffix_for(packet.default_format)}",
                mime=mime_for(packet.default_format),
                key=f"{key_prefix}_pk_{pk_key}_{report.report_id}",
            )
        except Exception:  # pragma: no cover - defensive
            st.caption(f"{packet.name} unavailable.")


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


def render_executive_report_workspace(repository_factory: RepositoryFactory, *, insights_fn=None) -> None:
    """Render the Executive Hiring Report workspace (pick candidate + template → run)."""
    st.title("📊 Executive Hiring Report")
    st.caption(
        "TalentMind's Executive Decision Layer — it turns all existing hiring "
        "intelligence into a boardroom-ready briefing for CTOs, CEOs, HR directors, "
        "hiring managers and recruiters. Consumes existing outputs only."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Report data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available.")
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 2])
    chosen = cols[0].selectbox("Candidate", ids, key="er_pick")
    template_keys = [t.key for t in TEMPLATES.values()]
    template = cols[1].selectbox(
        "Report template",
        template_keys,
        format_func=lambda k: get_template(k).name,
        key="er_template",
    )
    st.caption(get_template(template).summary)
    jd_text = st.text_area("Optional job description (sharpens role-fit)", key="er_jd")

    if st.button("📊 Generate executive report", type="primary", key="er_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_executive_report(
                candidate, jd=jd_text, template=template, insights_fn=insights_fn, key_prefix="er_ws"
            )
