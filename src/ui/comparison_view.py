"""Candidate Comparison Workspace UI (Module 2 UI).

Reads the comparison shortlist from session state, builds a
:class:`ComparisonReport` from the shared (cached) insight bundles, and renders a
professional side-by-side dashboard: a metric matrix with per-metric leaders
highlighted, plus qualitative panels (strengths, weaknesses, summaries, interview
focus, missing skills) for each candidate.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.comparison.builder import build_comparison
from src.comparison.models import ComparisonReport
from src.models.candidates import Candidate
from src.ui.helpers import get_insights
from src.ui.workspace_state import clear_compare, get_compare_ids

# Human labels for the numeric metric attributes, in display order.
_METRIC_LABELS = [
    ("overall_score", "Overall Score"),
    ("hiring_recommendation", "Hiring Recommendation"),
    ("timeline_score", "Timeline Score"),
    ("risk_score", "Risk Score"),
    ("technical_score", "Technical Score"),
    ("leadership_score", "Leadership Score"),
    ("experience_score", "Experience Score"),
    ("career_growth", "Career Growth"),
    ("skill_match", "Skill Match %"),
]


def render_comparison_workspace(candidate_by_id: dict[str, Candidate], jd: str) -> None:
    """Render the comparison workspace for the shortlisted candidates.

    Args:
        candidate_by_id: Lookup from candidate id to the candidate object (for
            every ranked candidate, so any shortlisted id can be resolved).
        jd: Raw job-description text (for skill-match computation).
    """
    st.subheader("🆚 Candidate Comparison")

    selected_ids = [cid for cid in get_compare_ids() if cid in candidate_by_id]

    if not selected_ids:
        st.info(
            "Select candidates with **➕ Compare** on their cards below "
            "(up to 5) to see a side-by-side breakdown here."
        )
        return

    top = st.columns([4, 1])
    top[0].caption(f"Comparing {len(selected_ids)} candidate(s).")
    if top[1].button("Clear", key="cmp_clear"):
        clear_compare()
        _rerun()

    insights = [get_insights(candidate_by_id[cid], jd) for cid in selected_ids]
    report = build_comparison(insights)

    _render_matrix(report)
    _render_qualitative(report)


def _render_matrix(report: ComparisonReport) -> None:
    """Render the numeric/label metric matrix (metrics × candidates)."""
    rows = report.rows
    columns = [f"{r.title}\n({r.candidate_id})" for r in rows]

    data = {}
    for attr, label in _METRIC_LABELS:
        values = []
        for row in rows:
            raw = getattr(row, attr)
            if attr == "hiring_recommendation":
                values.append(str(raw))
            else:
                leader = report.best_by_metric.get(attr) == row.candidate_id
                marker = " 🏆" if leader else ""
                values.append(f"{raw:.1f}{marker}")
        data[label] = values

    frame = pd.DataFrame(data, index=columns).T
    frame.columns = columns
    st.dataframe(frame, use_container_width=True)
    st.caption("🏆 marks the leading candidate for each numeric metric.")


def _render_qualitative(report: ComparisonReport) -> None:
    """Render per-candidate qualitative panels side by side."""
    st.markdown("#### Qualitative Breakdown")
    columns = st.columns(len(report.rows))

    for column, row in zip(columns, report.rows):
        with column:
            st.markdown(f"**{row.title}**")
            st.caption(f"{row.company} · {row.candidate_id}")
            st.markdown(f"_{row.hiring_recommendation}_")

            _bullets("💪 Strengths", row.strengths, "success")
            _bullets("⚠ Weaknesses", row.weaknesses, "warning")
            _bullets("🎯 Interview Focus", row.interview_focus, "info")
            _bullets("❌ Missing Skills", row.missing_skills, "error")

            if row.recruiter_summary:
                with st.expander("Recruiter Summary"):
                    for line in row.recruiter_summary:
                        st.write("•", line)


def _bullets(title: str, items, style: str) -> None:
    """Render a titled list of short items using a status style, if non-empty."""
    if not items:
        return
    st.markdown(f"**{title}**")
    renderer = {
        "success": st.success,
        "warning": st.warning,
        "info": st.info,
        "error": st.error,
    }.get(style, st.write)
    for item in items[:5]:
        renderer(item)


def _rerun() -> None:
    """Trigger a Streamlit rerun, tolerant of Streamlit version differences."""
    rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
    if rerun is not None:
        rerun()
