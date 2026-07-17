"""AI Hiring Committee dashboard (Module 10).

An enterprise workspace that makes the committee's deliberation fully
transparent (Module 8): a consensus meter, per-member opinion cards (who said
what, with evidence + confidence), conflict cards, a discussion timeline, the
five explained confidence signals, and the executive decision card. Styling is
consistent with the Resume / JD Intelligence workspaces.

Presentation only — all reasoning comes from :class:`HiringCommitteeEngine`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from src.ai.committee.committee import HiringCommitteeEngine
from src.ai.committee.schemas import CommitteeMode, CommitteeReport
from src.ai.core.runner import AgentRunner
from src.ui.theme import empty_state

_runner: AgentRunner | None = None
_engine: HiringCommitteeEngine | None = None


def _get_engine(insights_fn=None) -> HiringCommitteeEngine:
    """Return a shared committee engine (offline/local defaults)."""
    global _runner, _engine
    if _runner is None:
        _runner = AgentRunner()
    if _engine is None or insights_fn is not None:
        _engine = HiringCommitteeEngine(insights_fn=insights_fn, ai_runner=_runner)
    return _engine


def render_committee(
    candidate: Any,
    *,
    jd: str = "",
    mode: str = "balanced",
    insights_fn=None,
    key_prefix: str = "cm",
) -> None:
    """Convene the committee for a candidate and render the full dashboard."""
    st.subheader("AI Hiring Committee")
    st.caption(
        "A panel of AI specialists independently reviews the existing engine "
        "outputs, debates, resolves conflicts and produces one transparent, "
        "evidence-backed decision. No engine is re-run; nothing is fabricated."
    )

    with st.spinner("Convening the committee…"):
        engine = _get_engine(insights_fn)
        report = engine.run(candidate=candidate, jd=jd, mode=CommitteeMode(mode))

    _render_report(report)


def _render_report(report: CommitteeReport) -> None:
    """Render a full :class:`CommitteeReport`."""
    consensus = report.consensus
    decision = report.decision

    # -- headline ----------------------------------------------------------
    top = st.columns(4)
    top[0].metric("Recommendation", consensus.recommendation.value)
    top[1].metric("Consensus", consensus.level.value)
    top[2].metric("Confidence", f"{report.confidence.overall:.0f}/100")
    top[3].metric("Conflicts", len(report.conflicts))

    # Consensus meter: map weighted stance (-2..3) onto 0..1.
    meter = max(0.0, min(1.0, (consensus.weighted_stance + 2.0) / 5.0))
    st.caption(
        f"Consensus meter (No Hire to Strong Hire) · stance {consensus.weighted_stance:+.2f}"
    )
    st.progress(meter)

    for warning in report.warnings:
        st.warning(warning)

    tabs = st.tabs(["Decision", "Opinions", "Discussion", "Conflicts", "Confidence", "Report"])

    with tabs[0]:
        st.info(decision.executive_summary)
        st.markdown("**Business justification**")
        st.write(decision.business_justification)
        st.markdown("**Technical justification**")
        st.write(decision.technical_justification)
        c = st.columns(2)
        with c[0]:
            st.markdown("**Hiring risks**")
            _bullets(decision.hiring_risks, "None flagged.")
            st.markdown("**Remaining unknowns**")
            _bullets(decision.remaining_unknowns, "None.")
        with c[1]:
            st.markdown("**Interview priorities**")
            _bullets(decision.interview_priorities, "None.")
            st.markdown("**Follow-up actions**")
            _bullets(decision.follow_up_actions, "None.")
        st.caption(decision.confidence_note)

    with tabs[1]:
        st.caption("Each specialist reviewed independently (no member saw another's opinion).")
        st.caption("Consensus reasoning: " + consensus.reasoning)
        for opinion in report.opinions:
            weight = consensus.member_weights.get(opinion.role, 0.0)
            with st.expander(
                f"{opinion.role_title} — {opinion.recommendation.value} "
                f"(confidence {opinion.confidence:.0f}%, weight {weight:.2f})"
                + (" · abstained" if opinion.abstained else "")
            ):
                st.write(opinion.opinion)
                if opinion.strengths:
                    st.markdown("**Strengths**")
                    _bullets(opinion.strengths, "")
                if opinion.concerns:
                    st.markdown("**Concerns**")
                    _bullets(opinion.concerns, "")
                st.markdown("**Evidence**")
                _bullets(opinion.evidence, "No evidence cited.")

    with tabs[2]:
        st.markdown("**Agreements**")
        _bullets(report.discussion.agreements, "No groupings.")
        st.markdown("**Disagreements**")
        _bullets(report.discussion.disagreements, "No directional disagreement.")
        st.markdown("**Challenges (evidence-backed)**")
        if not report.discussion.challenges:
            st.caption("No challenges raised.")
        for ch in report.discussion.challenges:
            st.markdown(f"- {ch.get('claim', '')}")
            st.caption(
                f"Evidence: {ch.get('evidence', '')} · confidence gap {ch.get('confidence_gap', 0)}"
            )
        if report.discussion.missing_evidence:
            st.markdown("**Missing evidence**")
            _bullets(report.discussion.missing_evidence, "")

    with tabs[3]:
        if not report.conflicts:
            st.success("No material conflicts — the panel's differences are only of degree.")
        for conflict in report.conflicts:
            with st.expander(
                f"{conflict.member_a} vs {conflict.member_b} (gap {conflict.stance_gap:.0f})"
            ):
                st.markdown(f"**Root cause:** {conflict.root_cause}")
                st.markdown(f"**Missing evidence:** {conflict.missing_evidence}")
                st.markdown(f"**Different assumptions:** {conflict.assumption_difference}")
                st.caption(conflict.confidence_difference)
                st.success("Resolution: " + conflict.resolution_strategy)

    with tabs[4]:
        conf = report.confidence
        metrics = {
            "Evidence Coverage": conf.evidence_coverage,
            "Consensus Strength": conf.consensus_strength,
            "Confidence Distribution": conf.confidence_distribution,
            "Decision Stability": conf.decision_stability,
            "Unknown Risk (lower better)": conf.unknown_risk,
        }
        for name, value in metrics.items():
            st.caption(f"{name} — {value:.0f}/100")
            st.progress(min(1.0, max(0.0, value / 100.0)))
        st.markdown("**Why these values?**")
        for key, text in conf.explanations.items():
            st.caption(f"• {text}")

    with tabs[5]:
        st.markdown(
            f"**Candidate:** {report.candidate_overview.get('title')} @ {report.candidate_overview.get('company')}"
        )
        st.markdown("**Resume summary:** " + report.resume_summary)
        st.markdown("**JD summary:** " + report.jd_summary)
        st.markdown("**Consensus matrix (stance distribution)**")
        st.write(consensus.stance_distribution)
        st.caption("Evidence sources: " + ", ".join(report.evidence_sources))
        st.caption(f"Meeting id: {report.meeting_id} · mode: {report.mode}")


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


def render_committee_workspace(repository_factory: RepositoryFactory, *, insights_fn=None) -> None:
    """Render the Hiring Committee workspace (pick candidate + JD + mode → run)."""
    st.title("AI Hiring Committee")
    st.caption(
        "TalentMind's flagship multi-agent decision engine — an executive hiring "
        "panel that debates the evidence and produces a transparent recommendation."
    )

    try:
        repository = repository_factory()
    except Exception as exc:
        st.error(f"Committee data is not ready: {exc}")
        return

    candidates = repository.sample(limit=50)
    if not candidates:
        empty_state(
            "No candidates available",
            "Load a candidate dataset to convene the hiring committee.",
        )
        return

    ids = [c.candidate_id for c in candidates]
    cols = st.columns([2, 1])
    chosen = cols[0].selectbox("Candidate", ids, key="cm_pick")
    mode = cols[1].selectbox(
        "Committee mode", ["balanced", "optimistic", "conservative"], key="cm_mode"
    )
    jd_text = st.text_area("Optional job description (sharpens role-fit)", key="cm_jd")

    if st.button("Convene committee", type="primary", key="cm_run"):
        candidate = repository.get(chosen)
        if candidate is not None:
            render_committee(
                candidate, jd=jd_text, mode=mode, insights_fn=insights_fn, key_prefix="cm_ws"
            )
