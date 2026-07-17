"""Enterprise Hiring Workspace orchestrator (Module 7).

A single entry point (:func:`render_enterprise_workspace`) that app.py calls with
one line. It computes the shared, bounded insight cohort **once** and fans it out
to the four workspace surfaces — Analytics, Talent Pools, Smart Filters and
Comparison — each rendered in its own tab so the page stays uncluttered.

Keeping the orchestration here (rather than in app.py) preserves the "thin
orchestrator" architecture: app.py gains one import and one call.
"""

from __future__ import annotations

import streamlit as st

from src.insights.models import CandidateInsights
from src.models.candidates import Candidate
from src.pipeline.store import PipelineStore
from src.ui.analytics_dashboard import render_enterprise_dashboard
from src.ui.comparison_view import render_comparison_workspace
from src.ui.filters_panel import render_smart_filters
from src.ui.helpers import get_insights
from src.ui.talent_pool_view import render_talent_pools

# Size of the insight cohort used for engine-backed analytics / segmentation /
# filtering. Bounding this keeps the workspace responsive on large datasets: the
# expensive intelligence engines run for the top-ranked candidates only, and each
# result is cached per candidate for the session (see ``get_insights``).
ANALYTICS_COHORT = 40


def render_enterprise_workspace(
    candidates: list[Candidate],
    results: list[tuple[Candidate, float]],
    jd: str,
) -> None:
    """Render the full Enterprise Hiring Workspace.

    Args:
        candidates: Full candidate pool (used for field-only dashboard charts).
        results: Ranked ``(candidate, score)`` tuples, highest first.
        jd: Raw job-description text.
    """
    st.header("Enterprise Hiring Workspace")

    if not results:
        st.info("Rank candidates to unlock the enterprise workspace.")
        return

    candidate_by_id: dict[str, Candidate] = {
        candidate.candidate_id: candidate for candidate, _ in results
    }

    cohort = results[:ANALYTICS_COHORT]
    with st.spinner("Preparing candidate intelligence for the workspace..."):
        insights: list[CandidateInsights] = [
            get_insights(candidate, jd, score) for candidate, score in cohort
        ]

    pipeline_states = PipelineStore().load()

    tab_dashboard, tab_pools, tab_filters, tab_compare = st.tabs(
        ["Dashboard", "Talent Pools", "Smart Filters", "Compare"]
    )

    with tab_dashboard:
        render_enterprise_dashboard(candidates, insights, pipeline_states)

    with tab_pools:
        render_talent_pools(insights)

    with tab_filters:
        render_smart_filters(insights, pipeline_states)

    with tab_compare:
        render_comparison_workspace(candidate_by_id, jd)

    st.divider()
