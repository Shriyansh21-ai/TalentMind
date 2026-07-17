"""Enterprise Hiring Audit & Explainability workspace (Modules 9, 10, 11).

A professional audit workspace that renders the unified :class:`HiringAuditReport`:
the decision trace, evidence provenance, evidence graph, reasoning registers, the
timeline, the human-vs-AI responsibility matrix, governance explanations, audit
readiness, historical reconstruction and an enterprise dashboard.

Presentation only — all reasoning comes from :class:`HiringAuditEngine`, which
reconstructs the journey from artefacts on record, never fabricates and gives no
legal opinion. Unverified/absent items are clearly marked.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.ai.agents.audit.audit_engine import HiringAuditEngine
from src.ai.agents.audit.schemas import HiringAuditReport
from src.ai.core.runner import AgentRunner

_runner: AgentRunner | None = None
_engine: HiringAuditEngine | None = None


def _get_engine(insights_fn=None) -> HiringAuditEngine:
    """Return a shared audit engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = HiringAuditEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_audit(
    candidate: Any,
    *,
    jd: str = "",
    insights_fn=None,
    generated_on: str = "",
    key_prefix: str = "au",
) -> None:
    """Build the audit report for a candidate and render the workspace."""
    st.subheader("🔎 Enterprise Hiring Audit & Explainability")
    st.caption(
        "Reconstructs the complete hiring journey — why the decision was made, "
        "which AI agents participated, which evidence influenced it, which "
        "assumptions were made and which human approvals occurred. It reconstructs "
        "only artefacts on record; it never fabricates evidence, approvals or "
        "history, and gives no legal opinion."
    )

    with st.spinner("Reconstructing the hiring decision journey…"):
        engine = _get_engine(insights_fn)
        report = engine.build(candidate=candidate, jd=jd, generated_on=generated_on)

    _render_report(report, key_prefix=key_prefix)


_STATUS_BADGE = {
    "Observed": "✅",
    "Complete": "✅",
    "Ready": "✅",
    "Unavailable": "➖",
    "Unverified": "⚠️",
    "Partially Ready": "⚠️",
    "Not Ready": "❌",
    "Requires Review": "⚠️",
}


def _badge(status: str) -> str:
    return _STATUS_BADGE.get(status, "•")


def _render_report(report: HiringAuditReport, *, key_prefix: str) -> None:
    """Render a full :class:`HiringAuditReport`."""
    narrative = report.narrative
    readiness = report.audit_readiness

    top = st.columns(5)
    top[0].metric("Agents", len(report.agents_participated))
    top[1].metric("Audit Readiness", readiness.status)
    top[2].metric("Level", readiness.readiness_level)
    ai_count = sum(
        1 for d in report.responsibility if d.responsible_party == "AI" and d.status == "Observed"
    )
    human_count = sum(
        1 for d in report.responsibility if d.responsible_party != "AI" and d.status == "Observed"
    )
    top[3].metric("AI Decisions", ai_count)
    top[4].metric("Verified Approvals", human_count)

    if not report.data_available:
        st.info(
            "ℹ️ No audit archive connected — human approvals and historical decisions are unverified; the reconstruction reflects on-record artefacts only (Module 14)."
        )
    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "📄 Summary",
            "🧭 Decision Trace",
            "🔗 Evidence & Provenance",
            "🕸️ Evidence Graph",
            "🧠 Reasoning",
            "⏱️ Timeline",
            "👥 Human vs AI",
            "🏛️ Governance",
            "✅ Audit Readiness",
            "📚 History",
            "📊 Dashboard",
        ]
    )

    with tabs[0]:
        st.info(narrative.executive_summary)
        st.caption("🔎 " + narrative.data_availability_note)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Key findings**")
            _bullets(narrative.key_findings, "")
            st.markdown("**Audit recommendations**")
            _bullets(narrative.audit_recommendations, "")
        with c[1]:
            st.markdown("**Outstanding risks**")
            _bullets(narrative.outstanding_risks, "")
            st.markdown("**Assumptions**")
            _bullets(narrative.assumptions, "")
        st.caption("📌 " + narrative.confidence_note)

    with tabs[1]:
        st.caption(narrative.decision_journey_note)
        for s in report.decision_trace:
            st.markdown(
                f"{_badge(s.status)} **{s.order}. {s.stage}** — {s.status}  _({s.origin_agent})_"
            )
            st.caption(s.summary)

    with tabs[2]:
        st.caption(narrative.evidence_note)
        for p in report.provenance:
            st.markdown(f"{_badge(p.register)} **{p.evidence_source}** — {p.evidence_type}")
            st.caption(
                f"Origin: {p.origin_agent} · confidence: {p.confidence} · register: {p.register}"
            )

    with tabs[3]:
        graph = report.evidence_graph
        st.markdown("**Nodes**")
        st.caption(", ".join(f"{'●' if n.present else '○'} {n.label}" for n in graph.nodes))
        st.markdown("**Active edges (evidence flow)**")
        for e in graph.edges:
            if e.active:
                st.caption(f"{e.source} → {e.target}")

    with tabs[4]:
        r = report.reasoning
        for title, items in [
            ("Observed facts", r.observed_facts),
            ("Derived insights", r.derived_insights),
            ("Business reasoning", r.business_reasoning),
            ("Assumptions", r.assumptions),
            ("AI decisions", r.ai_decisions),
            ("Human decisions", r.human_decisions),
        ]:
            st.markdown(f"**{title}**")
            _bullets(items, "None recorded.")

    with tabs[5]:
        for t in report.timeline:
            st.markdown(f"{_badge(t.status)} **{t.order}. {t.name}** · {t.actor} · {t.status}")
            st.caption(t.detail)

    with tabs[6]:
        st.caption(narrative.responsibility_note)
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**🤖 AI decisions**")
            for d in report.responsibility:
                if d.responsible_party == "AI":
                    st.caption(f"{_badge(d.status)} {d.decision} — {d.kind} ({d.status})")
        with cols[1]:
            st.markdown("**👤 Human decisions**")
            for d in report.responsibility:
                if d.responsible_party != "AI":
                    st.caption(
                        f"{_badge(d.status)} {d.decision} — {d.responsible_party} · {d.kind} ({d.status})"
                    )

    with tabs[7]:
        st.caption(narrative.governance_note)
        for g in report.governance_explanations:
            st.markdown(f"**{g.topic} — {g.question}**  _({g.register})_")
            st.caption(g.explanation)

    with tabs[8]:
        st.metric("Audit readiness", f"{readiness.status} ({readiness.readiness_level})")
        st.caption(readiness.governance_completeness)
        st.markdown("**Missing evidence**")
        _bullets(readiness.missing_evidence, "None.")
        st.markdown("**Missing documents**")
        _bullets(readiness.missing_documents, "None.")
        st.markdown("**Missing approvals**")
        _bullets(readiness.missing_approvals, "None.")
        st.markdown("**Unverified decisions**")
        _bullets(readiness.unverified_decisions, "None.")

    with tabs[9]:
        h = report.history
        if h.available:
            st.success(h.status_message)
            for rec in h.records:
                st.json(rec)
        else:
            st.info(h.status_message)
            st.caption(
                "Connect an audit archive (SIEM / DMS / compliance archive) to reconstruct past decisions (Module 12)."
            )

    with tabs[10]:
        _render_dashboard(report)


def _render_dashboard(report: HiringAuditReport) -> None:
    """Render the enterprise audit dashboard (Module 10)."""
    charts = report.charts
    ap = charts.get("agent_participation", {})
    st.markdown("**Agent participation**")
    st.progress(max(0.0, min(1.0, ap.get("ratio", 0.0))))
    st.caption(f"{ap.get('count', 0)}/{ap.get('total', 0)} catalog agents participated")

    st.markdown("**Decision flow**")
    st.caption(
        " → ".join(
            f"{s['stage']}{'' if s['status'] == 'Observed' else ' (—)'}"
            for s in charts.get("decision_flow", [])
        )
    )

    st.markdown("**Approval chain**")
    for step in charts.get("approval_chain", []):
        st.caption(
            f"{_badge(step.get('status'))} {step.get('decision')} ({step.get('party')}) — {step.get('status')}"
        )

    gh = charts.get("governance_health", {})
    st.markdown("**Governance health / audit readiness**")
    st.caption(
        " · ".join(f"**{s}**" if s == gh.get("readiness") else s for s in gh.get("scale", []))
    )

    ar = charts.get("audit_readiness", {})
    st.caption(
        f"Missing evidence: {ar.get('missing_evidence', 0)} · missing docs: {ar.get('missing_documents', 0)} · "
        f"missing approvals: {ar.get('missing_approvals', 0)} · unverified: {ar.get('unverified_decisions', 0)}"
    )


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


def render_audit_workspace(repository_factory: RepositoryFactory, *, insights_fn=None) -> None:
    """Render the Hiring Audit workspace (pick candidate → run)."""
    st.title("🔎 Enterprise Hiring Audit & Explainability")
    st.caption(
        "TalentMind's audit & explainability platform. It reconstructs the "
        "complete hiring journey with transparent, evidence-backed reasoning — "
        "clearly separating observed facts, inferred insights, AI recommendations "
        "and human decisions — making every decision fully auditable. It never "
        "fabricates history, evidence or approvals."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Audit data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available.")
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 3])
    chosen = cols[0].selectbox("Candidate", ids, key="au_pick")
    jd_text = cols[1].text_area(
        "Optional job description (sharpens the reconstruction)", key="au_jd"
    )

    if st.button("🔎 Reconstruct hiring decision", type="primary", key="au_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_audit(candidate, jd=jd_text, insights_fn=insights_fn, key_prefix="au_ws")
