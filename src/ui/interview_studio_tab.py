"""Enterprise AI Interview Studio workspace (Modules 9, 11, 12, 13).

A professional interview-preparation workspace that renders the unified
:class:`InterviewStudioReport`: an interview strategy, an adaptive roadmap
timeline, personalized technical / behavioral / role-specific questions,
risk-validation questions, evaluation rubrics, a decision matrix, feedback
templates, a live-interview assistant and a visual dashboard (timeline, coverage
radar, risk heatmap, question distribution, decision readiness).

Presentation only — all reasoning comes from :class:`InterviewStudioEngine`,
which consumes existing structured outputs and never re-ranks or fabricates.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.ai.agents.interview_studio.report import InterviewStudioEngine
from src.ai.agents.interview_studio.schemas import InterviewStudioReport
from src.ai.agents.interview_studio.templates import (
    DEPTH_PROFILES,
    ROLE_PROFILES,
    get_depth,
    get_role,
)
from src.ai.core.runner import AgentRunner

_runner: AgentRunner | None = None
_engine: InterviewStudioEngine | None = None


def _get_engine(insights_fn=None) -> InterviewStudioEngine:
    """Return a shared interview-studio engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = InterviewStudioEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_interview_studio(
    candidate: Any,
    *,
    jd: str = "",
    role: str = "",
    depth: str = "",
    insights_fn=None,
    key_prefix: str = "is",
) -> None:
    """Build the interview package for a candidate and render the full workspace."""
    st.subheader("Enterprise AI Interview Studio")
    st.caption(
        "A complete, personalized interview plan synthesized from every existing "
        "TalentMind intelligence source — committee, resume, JD, candidate "
        "intelligence, timeline, risk and recommendation. No engine is re-run; "
        "every question traces back to the evidence, and nothing is fabricated."
    )

    with st.spinner("Designing the interview plan…"):
        engine = _get_engine(insights_fn)
        report = engine.build(candidate=candidate, jd=jd, role=role, depth=depth)

    _render_report(report, key_prefix=key_prefix)


def _render_report(report: InterviewStudioReport, *, key_prefix: str) -> None:
    """Render a full :class:`InterviewStudioReport`."""
    narrative = report.narrative
    strategy = report.strategy

    top = st.columns(5)
    top[0].metric("Role Path", report.role_name)
    top[1].metric("Depth", get_depth(report.depth).name)
    top[2].metric("Readiness", narrative.readiness_label)
    top[3].metric("Questions", len(report.all_questions()))
    top[4].metric("Evidence Sources", len(report.evidence_sources))

    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(
        [
            "Strategy",
            "Roadmap",
            "Technical",
            "Behavioral",
            "Role-Specific",
            "Risk Validation",
            "Rubrics",
            "Decision Matrix",
            "Feedback",
            "Live Assistant",
            "Dashboard",
        ]
    )

    with tabs[0]:
        st.info(narrative.interview_summary)
        st.caption(strategy.summary)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Objectives**")
            _bullets(strategy.objectives, "")
            st.markdown("**Priorities**")
            _bullets(strategy.priorities, "None flagged by the engines.")
        with c[1]:
            st.markdown("**Decision checkpoints**")
            _bullets(strategy.decision_checkpoints, "")
            st.caption(f"**Difficulty:** {strategy.difficulty}")
            st.caption(
                f"**Length:** {strategy.length_minutes} min across {strategy.stage_count} stages"
            )
        c2 = st.columns(2)
        with c2[0]:
            st.markdown("**Key probes**")
            _bullets(narrative.key_probes, "Confirm role fit and depth.")
        with c2[1]:
            st.markdown("**Watch areas**")
            _bullets(narrative.watch_areas, "None surfaced.")
        st.caption("" + narrative.confidence_note)
        st.caption("" + narrative.personalization_note)

    with tabs[1]:
        st.caption(narrative.coverage_note)
        for i, stage in enumerate(report.roadmap, start=1):
            with st.expander(
                f"{i}. {stage.name} · {stage.duration_minutes} min · {stage.interviewer}",
                expanded=(i <= 2),
            ):
                st.write(stage.objective)
                if stage.focus:
                    st.markdown("**Focus:**")
                    _bullets(stage.focus, "")
                if stage.checkpoint:
                    st.caption("Checkpoint: " + stage.checkpoint)

    with tabs[2]:
        _render_questions(report.technical_questions, "No technical questions generated.")
    with tabs[3]:
        _render_questions(report.behavioral_questions, "No behavioral questions generated.")
    with tabs[4]:
        st.caption(f"Specialized questions for the **{report.role_name}** path.")
        _render_questions(report.role_specific_questions, "No role-specific questions generated.")

    with tabs[5]:
        st.caption(narrative.risk_validation_note)
        for rv in report.risk_validations:
            with st.expander(f"[{rv.category}] {rv.risk}"):
                st.markdown(f"**Validation question:** {rv.validation_question}")
                st.markdown(f"**Expected evidence:** {rv.expected_evidence}")
                st.markdown(f"**Pass criteria:** {rv.pass_criteria}")
                st.caption("Source: " + rv.source)

    with tabs[6]:
        st.caption("Score each dimension Strong / Solid / Mixed / Weak against the bar below.")
        for dim in report.rubrics:
            with st.expander(f"{dim.name} — {dim.weight}"):
                st.write(dim.description)
                for level, descriptor in dim.levels.items():
                    st.markdown(f"- **{level}:** {descriptor}")
                if dim.evidence_to_look_for:
                    st.markdown("**Evidence to look for:**")
                    _bullets(dim.evidence_to_look_for, "")

    with tabs[7]:
        matrix = report.decision_matrix
        st.info(matrix.committee_alignment)
        cols = st.columns(len(matrix.bands))
        for col, band in zip(cols, matrix.bands):
            with col:
                st.markdown(f"### {band.label}")
                st.caption(f"Confidence: {band.confidence_label}")
                _bullets(band.signals, "")
                if band.escalation:
                    st.caption("" + band.escalation)
        st.markdown("**Escalation criteria**")
        _bullets(matrix.escalation_criteria, "")

    with tabs[8]:
        forms = report.feedback_forms
        st.markdown("**Interviewer feedback form**")
        _bullets(forms.interviewer_form, "")
        st.markdown("**Hiring-manager feedback**")
        _bullets(forms.hiring_manager_form, "")
        st.markdown("**Panel feedback**")
        _bullets(forms.panel_form, "")
        st.markdown("**Candidate feedback summary (template)**")
        _bullets(forms.candidate_summary_template, "")

    with tabs[9]:
        la = report.live_assistant
        st.caption(
            "Real-time interviewer support. No voice/AI features yet — structured hooks only."
        )
        c = st.columns(2)
        with c[0]:
            st.markdown("**Notes template**")
            _bullets(la.interviewer_notes_template, "")
            st.markdown("**Question checklist**")
            _bullets(la.question_checklist, "")
            st.markdown("**Follow-up prompts**")
            _bullets(la.followup_suggestions, "")
        with c[1]:
            st.markdown("**Evaluation checklist**")
            _bullets(la.evaluation_checklist, "")
            st.markdown("**Risk reminders**")
            _bullets(la.risk_reminders, "None.")
            st.markdown("**Timer hooks**")
            for hook in la.timer_hooks:
                st.caption(
                    f"{hook['at_minute']} min — {hook['stage']} ({hook['duration_minutes']} min)"
                )

    with tabs[10]:
        _render_dashboard(report)


def _render_questions(questions: list[Any], empty: str) -> None:
    """Render a list of :class:`InterviewQuestion` grouped by difficulty."""
    if not questions:
        st.info(empty)
        return
    for q in questions:
        with st.expander(f"[{q.difficulty}] {q.competency}: {q.text}"):
            if q.expected_answer:
                st.markdown(f"**Expected answer:** {q.expected_answer}")
            if q.evaluation_criteria:
                st.markdown("**Evaluation criteria:**")
                _bullets(q.evaluation_criteria, "")
            if q.signals:
                st.caption("Signals: " + ", ".join(q.signals))
            st.caption("Source: " + q.source)


def _render_dashboard(report: InterviewStudioReport) -> None:
    """Render the professional interview dashboard (Module 12)."""
    charts = report.charts
    cols = st.columns(3)
    cols[0].metric("Total Time", f"{charts.get('total_minutes', 0)} min")
    cols[1].metric("Stages", charts.get("stage_count", 0))
    cols[2].metric("Decision Readiness", f"{charts.get('decision_readiness', 0) * 100:.0f}%")

    st.markdown("**Competency coverage (question count per axis)**")
    _bar(charts.get("coverage_radar", {}))

    st.markdown("**Question distribution**")
    _bar(charts.get("question_distribution", {}))

    st.markdown("**Difficulty progression**")
    _bar(charts.get("difficulty_distribution", {}))

    st.markdown("**Risk heatmap (0 = none, 3 = high)**")
    heat = charts.get("risk_heatmap", {})
    for name, level in heat.items():
        st.caption(f"{name}: {'' * level or ''}")

    st.markdown("**Interview timeline**")
    for item in charts.get("timeline", []):
        st.caption(f"{item['start_minute']}–{item['end_minute']} min · {item['stage']}")


def _bar(data: dict) -> None:
    """Render a simple horizontal bar view for a ``{label: count}`` mapping."""
    if not data:
        st.caption("No data.")
        return
    peak = max([v for v in data.values() if isinstance(v, (int, float))] or [1]) or 1
    for label, value in data.items():
        if not isinstance(value, (int, float)):
            continue
        st.caption(f"{label}: {'▇' * int(round(value / peak * 12)) or '·'} {value}")


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


def render_interview_studio_workspace(
    repository_factory: RepositoryFactory, *, insights_fn=None
) -> None:
    """Render the Interview Studio workspace (pick candidate + role + depth → run)."""
    st.title("Enterprise AI Interview Studio")
    st.caption(
        "TalentMind's final hiring-lifecycle layer — it turns all existing hiring "
        "intelligence into recruiter-ready interview strategies, adaptive question "
        "flows, evaluation rubrics, interviewer packets and structured decision "
        "support. Consumes existing outputs only."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Interview data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        st.info("No candidates available.")
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 2, 2])
    chosen = cols[0].selectbox("Candidate", ids, key="is_pick")
    role_keys = ["(auto-detect)"] + [r.key for r in ROLE_PROFILES.values()]
    role_choice = cols[1].selectbox(
        "Role path",
        role_keys,
        format_func=lambda k: (
            "Auto-detect from title + JD" if k == "(auto-detect)" else get_role(k).name
        ),
        key="is_role",
    )
    depth_keys = ["(auto)"] + list(DEPTH_PROFILES)
    depth_choice = cols[2].selectbox(
        "Interview depth",
        depth_keys,
        format_func=lambda k: "Auto (from seniority)" if k == "(auto)" else get_depth(k).name,
        key="is_depth",
    )
    jd_text = st.text_area(
        "Optional job description (sharpens role-fit + risk validation)", key="is_jd"
    )

    if st.button("Generate interview plan", type="primary", key="is_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_interview_studio(
                candidate,
                jd=jd_text,
                role="" if role_choice == "(auto-detect)" else role_choice,
                depth="" if depth_choice == "(auto)" else depth_choice,
                insights_fn=insights_fn,
                key_prefix="is_ws",
            )
