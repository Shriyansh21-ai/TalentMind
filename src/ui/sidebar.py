"""Recruiter sidebar controls for TalentMind."""

from typing import Any

import streamlit as st


def render_sidebar() -> tuple[Any | None, bool]:
    """Render the recruiter sidebar (JD upload + rank trigger).

    Returns:
        A tuple of ``(uploaded_jd, run_button)`` where ``uploaded_jd`` is the
        uploaded file object (or ``None``) and ``run_button`` is ``True`` when
        the rank button was clicked this run.
    """
    st.sidebar.header("Recruiter Controls")

    uploaded_jd = st.sidebar.file_uploader(
        "Upload Job Description",
        type=["txt"],
    )

    run_button = st.sidebar.button(
        "🚀 Rank Candidates",
        use_container_width=True,
    )

    return uploaded_jd, run_button
