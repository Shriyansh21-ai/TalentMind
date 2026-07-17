"""AI Recruiter Copilot page (Modules 8-10).

An enterprise chat workspace: conversation panel, current-context sidebar, tool
execution visibility, suggested follow-ups, and one-click recruiter actions that
integrate with the existing pipeline/comparison/profile modules.

The page is UI-only: all reasoning happens in ``src/ai/copilot``. The candidate
repository is built lazily (on the first message) via an injected factory so the
page renders instantly and never loads the dataset just to show the chat.
"""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from src.ai.copilot.controller import RecruiterCopilot, build_recruiter_copilot
from src.ai.copilot.models import CopilotAction, CopilotTurn
from src.ai.services.hiring_analyst_service import get_platform_status
from src.ai.tools.base import CandidateRepository
from src.ui.theme import badge as tm_badge
from src.ui.theme import strip_emoji

RepositoryFactory = Callable[[], CandidateRepository]

_HISTORY_KEY = "copilot_history"
_PENDING_KEY = "copilot_pending"
_INSTANCE_KEY = "copilot_instance"
_SESSION_ID = "copilot_ui_session"

_STARTERS = [
    "Find senior machine learning engineers",
    "Give me an overview of the candidate pool",
    "What is the current hiring pipeline status?",
]


def render_copilot(
    repository_factory: RepositoryFactory,
    *,
    insights_fn=None,
    jd: str = "",
) -> None:
    """Render the AI Recruiter Copilot page.

    Args:
        repository_factory: Zero-arg callable returning a
            :class:`CandidateRepository` (built lazily on first use).
        insights_fn: Optional cached insights builder passed to the tools.
        jd: Current job-description context (optional).
    """
    st.title("AI Recruiter Copilot")
    st.caption(
        "An enterprise AI assistant that reasons over TalentMind's deterministic "
        "engines — evidence-based, never fabricated."
    )

    _ensure_state()
    _render_context_panel(jd)

    # Process any queued message (from a starter / follow-up / action button).
    pending = st.session_state.get(_PENDING_KEY)
    if pending:
        st.session_state[_PENDING_KEY] = None
        _handle_message(pending, repository_factory, insights_fn, jd)

    _render_history()
    _render_starters()

    prompt = st.chat_input("Ask the recruiter copilot…")
    if prompt:
        _handle_message(prompt, repository_factory, insights_fn, jd)
        _rerun()


# ---------------------------------------------------------------------------
# State + message handling
# ---------------------------------------------------------------------------


def _ensure_state() -> None:
    """Initialise session-state containers."""
    st.session_state.setdefault(_HISTORY_KEY, [])
    st.session_state.setdefault(_PENDING_KEY, None)
    st.session_state.setdefault(_INSTANCE_KEY, None)


def _get_copilot(repository_factory: RepositoryFactory, insights_fn) -> RecruiterCopilot | None:
    """Return (building lazily) the copilot instance, or ``None`` on failure."""
    if st.session_state.get(_INSTANCE_KEY) is None:
        try:
            repository = repository_factory()
        except Exception as exc:  # dataset/index not ready
            st.error(f"Copilot data is not ready: {exc}")
            return None
        st.session_state[_INSTANCE_KEY] = build_recruiter_copilot(
            repository, insights_fn=insights_fn
        )
    return st.session_state[_INSTANCE_KEY]


def _handle_message(
    message: str,
    repository_factory: RepositoryFactory,
    insights_fn,
    jd: str,
) -> None:
    """Run one message through the copilot and append the turn to history."""
    copilot = _get_copilot(repository_factory, insights_fn)
    if copilot is None:
        return
    with st.spinner("Thinking…"):
        turn = copilot.ask(_SESSION_ID, message, jd=jd)
    st.session_state[_HISTORY_KEY].append(turn)


def _queue(message: str) -> None:
    """Queue a message to be processed on the next run."""
    st.session_state[_PENDING_KEY] = message
    _rerun()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_context_panel(jd: str) -> None:
    """Render the current-context + platform indicators in the sidebar."""
    status = get_platform_status()
    with st.sidebar:
        st.markdown("### Copilot Context")
        st.caption(f"Provider: **{status['provider']}** · Model: **{status['model']}**")
        st.caption(f"Cache: {'on' if status['cache_enabled'] else 'off'}")

        copilot = st.session_state.get(_INSTANCE_KEY)
        if isinstance(copilot, RecruiterCopilot):
            state = copilot.session(_SESSION_ID).state
            st.markdown("**Working context**")
            st.caption(f"Focus candidate: {state.current_candidate or '—'}")
            st.caption(
                "Comparison set: "
                + (", ".join(state.current_comparison) if state.current_comparison else "—")
            )
            st.caption(f"Turns: {copilot.session(_SESSION_ID).turn_count}")

        if jd:
            st.caption("JD context: attached")

        if st.button("Clear conversation", key="copilot_clear"):
            st.session_state[_HISTORY_KEY] = []
            copilot = st.session_state.get(_INSTANCE_KEY)
            if isinstance(copilot, RecruiterCopilot):
                copilot.reset(_SESSION_ID)
            _rerun()


def _render_history() -> None:
    """Render the full conversation."""
    history: list[CopilotTurn] = st.session_state.get(_HISTORY_KEY, [])
    for index, turn in enumerate(history):
        with st.chat_message("user"):
            st.write(turn.message)
        with st.chat_message("assistant"):
            _render_turn(turn, index)


def _render_turn(turn: CopilotTurn, index: int) -> None:
    """Render one assistant turn: answer, indicators, tools, actions, follow-ups."""
    st.markdown(turn.answer)

    # Provenance indicators.
    badge = "cached" if turn.cache_hit else "generated"
    bits = [
        f"intent: {turn.intent.value}",
        badge,
        f"provider: {turn.provider}",
        f"{turn.latency_ms:.0f} ms",
    ]
    st.caption(" · ".join(bits))
    if turn.confidence_note:
        st.caption(f"{turn.confidence_note}")

    # Tool visibility (Module 9).
    if turn.tools_used:
        with st.expander(f"Tools used ({len(turn.tools_used)})"):
            for tool in turn.tools_used:
                pill = (
                    tm_badge("ok", "success", size="sm")
                    if tool.get("ok")
                    else tm_badge("error", "danger", size="sm")
                )
                st.markdown(
                    f"{pill} **{tool.get('name')}** — {tool.get('summary') or tool.get('error', '')}",
                    unsafe_allow_html=True,
                )
                meta = (
                    f"confidence {tool.get('confidence', 0):.0f} · "
                    f"{tool.get('latency_ms', 0):.0f} ms"
                )
                sources = ", ".join(tool.get("evidence_sources", []))
                if sources:
                    meta += f" · evidence: {sources}"
                st.caption(meta)
            if turn.reasoning_summary:
                st.caption(f"{turn.reasoning_summary}")

    # Actions (Module 10).
    if turn.actions:
        st.markdown("**Actions**")
        cols = st.columns(min(len(turn.actions), 3))
        for i, action in enumerate(turn.actions):
            if cols[i % len(cols)].button(strip_emoji(action.label), key=f"act_{index}_{i}"):
                _execute_action(action)

    # Follow-ups (Module 7).
    if turn.follow_ups:
        st.markdown("**Suggested follow-ups**")
        cols = st.columns(min(len(turn.follow_ups), 3))
        for i, question in enumerate(turn.follow_ups):
            if cols[i % len(cols)].button(question, key=f"fu_{index}_{i}"):
                _queue(question)


def _render_starters() -> None:
    """Render starter prompts when the conversation is empty."""
    if st.session_state.get(_HISTORY_KEY):
        return
    st.markdown("#### Try asking")
    cols = st.columns(len(_STARTERS))
    for i, starter in enumerate(_STARTERS):
        if cols[i].button(starter, key=f"starter_{i}"):
            _queue(starter)


# ---------------------------------------------------------------------------
# Action execution (integrates with existing modules)
# ---------------------------------------------------------------------------


def _execute_action(action: CopilotAction) -> None:
    """Execute a recruiter action from a response.

    Pipeline mutations run against the existing pipeline engine; the rest are
    turned into follow-up copilot queries so the answer stays in-conversation.
    """
    action_type = action.type
    params = action.params

    if action_type == "move_to_shortlist" and params.get("candidate_id"):
        from src.pipeline.engine import update_stage

        try:
            update_stage(params["candidate_id"], "Shortlisted", actor="copilot")
            st.toast(f"{params['candidate_id']} moved to Shortlisted.")
        except Exception as exc:
            st.warning(f"Could not update pipeline: {exc}")
        return

    if action_type == "open_profile":
        st.info("Open this candidate in the Recruiter Console to view the full profile tabs.")
        return

    # Everything else becomes a natural-language follow-up to the copilot.
    cid = params.get("candidate_id")
    ids = params.get("candidate_ids", [])
    query_map = {
        "generate_interview_plan": f"Generate an interview plan for {cid}",
        "view_risk": f"What are the risks for {cid}?",
        "view_timeline": f"Show the career timeline for {cid}",
        "generate_hiring_report": f"Generate a hiring summary for {cid}",
        "analyze_candidate": f"Analyze {cid}",
        "compare_candidates": f"Compare {' and '.join(ids)}" if ids else "Compare the candidates",
    }
    follow_up = query_map.get(action_type)
    if follow_up:
        _queue(follow_up)


def _rerun() -> None:
    """Trigger a Streamlit rerun, tolerant of version differences."""
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun is not None:
        rerun()
