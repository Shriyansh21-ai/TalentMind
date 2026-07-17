"""Talent Pool Segmentation UI (Module 3 UI).

Segments the insight cohort into :class:`TalentPool` groups, shows pool sizes as
a bar chart, and lets recruiters drill into any pool to see its members and the
rationale behind each assignment.
"""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from src.dashboard import charts
from src.insights.models import CandidateInsights
from src.talent_pool.models import TalentPool
from src.talent_pool.segmentation import pool_counts, segment_pool


def render_talent_pools(insights: Sequence[CandidateInsights]) -> None:
    """Render talent-pool composition and a per-pool drill-down.

    Args:
        insights: The bounded insight cohort to segment.
    """
    st.subheader("Talent Pools")

    if not insights:
        st.info("No candidates available to segment.")
        return

    assignments = segment_pool(insights)
    counts = pool_counts(assignments)
    insight_by_id: dict[str, CandidateInsights] = {i.candidate_id: i for i in insights}

    # Composition chart.
    non_zero = [(name, count) for name, count in counts.items() if count > 0]
    non_zero.sort(key=lambda pair: pair[1], reverse=True)
    st.plotly_chart(
        charts.horizontal_count_bar(non_zero, "Talent Pool Sizes", color="#7c3aed"),
        use_container_width=True,
    )

    # Drill-down.
    populated = [name for name, count in counts.items() if count > 0]
    if not populated:
        st.caption("No candidates matched any pool for the current cohort.")
        return

    pool_value = st.selectbox("Explore a pool", populated, key="pool_select")
    pool = TalentPool(pool_value)

    members = [assignment for assignment in assignments.values() if assignment.in_pool(pool)]
    st.caption(f"{len(members)} candidate(s) in **{pool_value}**")

    for assignment in members[:25]:
        insight = insight_by_id.get(assignment.candidate_id)
        if insight is None:
            continue
        with st.expander(f"{insight.title} · {insight.company} ({insight.candidate_id})"):
            st.write(
                f"Overall {insight.intelligence.overall_score:.0f} · "
                f"Risk {insight.risk.risk_level} · "
                f"Experience {insight.years_of_experience:.1f} yrs"
            )
            reason = next(
                (r for r in assignment.rationale if r.startswith(pool_value)),
                None,
            )
            if reason:
                st.caption(reason)
