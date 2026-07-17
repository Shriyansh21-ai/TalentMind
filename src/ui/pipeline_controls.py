"""Recruiter pipeline controls rendered on each candidate card (Module 1 UI).

Thin presentation wrapper over ``src/pipeline/engine.py``. It surfaces the
candidate's current stage + priority, offers only *valid* next-stage
transitions (validation is enforced by the engine, but the UI also hides illegal
options for a clean experience), and lets recruiters assign an owner, change
priority and drop a note — all persisted to the dedicated pipeline store.
"""

from __future__ import annotations

import streamlit as st

from src.models.candidates import Candidate
from src.pipeline.engine import (
    add_note,
    assign_recruiter,
    change_priority,
    get_or_create,
    update_stage,
)
from src.pipeline.models import Priority, allowed_transitions

_PRIORITY_VALUES = [p.value for p in Priority]


def render_pipeline_controls(candidate: Candidate) -> None:
    """Render the pipeline workflow controls for a single candidate.

    Args:
        candidate: The candidate whose pipeline state is being managed.
    """
    cid = candidate.candidate_id
    status = get_or_create(cid)

    st.markdown("#### 🧭 Hiring Pipeline")

    header = st.columns(3)
    header[0].metric("Stage", status.current_stage.value)
    header[1].metric("Status", status.status)
    header[2].metric("Priority", status.priority.value)

    # -- Stage transition (only valid moves offered) ------------------------
    targets = sorted(
        {status.current_stage, *allowed_transitions(status.current_stage)},
        key=lambda s: s.value,
    )
    target_values = [s.value for s in targets]
    current_index = target_values.index(status.current_stage.value)

    move_col, prio_col = st.columns(2)

    with move_col:
        chosen = st.selectbox(
            "Move to stage",
            target_values,
            index=current_index,
            key=f"stage_sel_{cid}",
        )
        if st.button("Apply stage", key=f"stage_btn_{cid}"):
            if chosen != status.current_stage.value:
                update_stage(cid, chosen, actor="recruiter")
                st.success(f"Moved to {chosen}")
                _rerun()

    with prio_col:
        new_priority = st.selectbox(
            "Priority",
            _PRIORITY_VALUES,
            index=_PRIORITY_VALUES.index(status.priority.value),
            key=f"prio_sel_{cid}",
        )
        if st.button("Set priority", key=f"prio_btn_{cid}"):
            if new_priority != status.priority.value:
                change_priority(cid, new_priority)
                st.success(f"Priority set to {new_priority}")
                _rerun()

    # -- Ownership + note ---------------------------------------------------
    recruiter = st.text_input(
        "Assigned recruiter",
        value=status.assigned_recruiter or "",
        key=f"rec_{cid}",
    )
    note = st.text_input(
        "Add note", key=f"note_{cid}", placeholder="e.g. Strong system-design signal"
    )

    action_col = st.columns(2)
    with action_col[0]:
        if st.button("Save recruiter", key=f"rec_btn_{cid}"):
            assign_recruiter(cid, recruiter.strip() or None)
            st.success("Recruiter updated")
            _rerun()
    with action_col[1]:
        if st.button("Save note", key=f"note_btn_{cid}"):
            if note.strip():
                add_note(cid, note.strip(), actor="recruiter")
                st.success("Note added")
                _rerun()

    if status.notes:
        with st.expander(f"Notes ({len(status.notes)})"):
            for line in status.notes[-10:]:
                st.caption(line)


def _rerun() -> None:
    """Trigger a Streamlit rerun, tolerant of Streamlit version differences."""
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun is not None:
        rerun()
