"""Session-state helpers for the Enterprise Hiring Workspace UI.

Centralizes the small amount of cross-widget state (currently the candidate
comparison shortlist) so no other UI module manipulates ``st.session_state`` keys
directly. Keeping this in one place avoids the classic Streamlit bug of two
modules disagreeing on a state key.
"""

from __future__ import annotations

import streamlit as st

_COMPARE_KEY = "workspace_compare_ids"
MAX_COMPARE = 5


def _ensure() -> None:
    """Initialise the comparison list in session state if absent."""
    if _COMPARE_KEY not in st.session_state:
        st.session_state[_COMPARE_KEY] = []


def get_compare_ids() -> list[str]:
    """Return the currently selected comparison candidate ids (ordered)."""
    _ensure()
    return list(st.session_state[_COMPARE_KEY])


def is_selected(candidate_id: str) -> bool:
    """Return ``True`` iff ``candidate_id`` is in the comparison shortlist."""
    _ensure()
    return candidate_id in st.session_state[_COMPARE_KEY]


def toggle_compare(candidate_id: str) -> None:
    """Add / remove a candidate from the shortlist, respecting the size cap.

    Adding beyond :data:`MAX_COMPARE` is a no-op that surfaces a toast so the
    recruiter understands why nothing changed.
    """
    _ensure()
    current: list[str] = st.session_state[_COMPARE_KEY]
    if candidate_id in current:
        current.remove(candidate_id)
    elif len(current) < MAX_COMPARE:
        current.append(candidate_id)
    else:
        st.toast(f"You can compare at most {MAX_COMPARE} candidates.")
    st.session_state[_COMPARE_KEY] = current


def clear_compare() -> None:
    """Empty the comparison shortlist."""
    st.session_state[_COMPARE_KEY] = []
