"""Enterprise recruiter analytics dashboard UI (Module 5 UI).

Wires the pure aggregations (``src/dashboard/analytics.py``) and Plotly figure
builders (``src/dashboard/charts.py``) into a professional, two-column dashboard.

Cheap, field-only charts (experience, skills, location, company) run over the
full candidate pool; engine-backed charts (score, risk, recommendation) run over
the bounded insight cohort the workspace already computed, and the pipeline
charts run over the persisted pipeline state — so nothing here recomputes
intelligence or re-reads the dataset.
"""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from src.dashboard import analytics, charts
from src.insights.models import CandidateInsights
from src.models.candidates import Candidate
from src.pipeline.models import CandidatePipelineStatus


def render_enterprise_dashboard(
    candidates: Sequence[Candidate],
    insights: Sequence[CandidateInsights],
    pipeline_states: dict[str, CandidatePipelineStatus],
) -> None:
    """Render the full enterprise analytics dashboard.

    Args:
        candidates: Full candidate pool (field-only charts).
        insights: Bounded insight cohort (engine-backed charts).
        pipeline_states: Persisted pipeline state map (workflow charts).
    """
    st.subheader("📈 Enterprise Analytics")
    st.caption(
        f"Field analytics over {len(candidates):,} candidates · "
        f"intelligence analytics over the top {len(insights):,} ranked · "
        f"pipeline analytics over {len(pipeline_states):,} tracked."
    )

    states: list[CandidatePipelineStatus] = list(pipeline_states.values())

    # -- Pipeline row -------------------------------------------------------
    stage_counts = analytics.stage_distribution(states)
    row1 = st.columns(2)
    row1[0].plotly_chart(
        charts.hiring_funnel(analytics.funnel_counts(states)),
        use_container_width=True,
    )
    row1[1].plotly_chart(charts.pipeline_chart(stage_counts), use_container_width=True)

    st.plotly_chart(charts.stage_distribution_chart(stage_counts), use_container_width=True)

    # -- Intelligence row ---------------------------------------------------
    row2 = st.columns(2)
    row2[0].plotly_chart(
        charts.score_distribution_chart(analytics.score_distribution(insights)),
        use_container_width=True,
    )
    row2[1].plotly_chart(
        charts.risk_distribution_chart(analytics.risk_distribution(insights)),
        use_container_width=True,
    )

    st.plotly_chart(
        charts.recommendation_distribution_chart(analytics.recommendation_distribution(insights)),
        use_container_width=True,
    )

    # -- Cohort composition row --------------------------------------------
    row3 = st.columns(2)
    row3[0].plotly_chart(
        charts.experience_distribution_chart(analytics.experience_distribution(candidates)),
        use_container_width=True,
    )
    row3[1].plotly_chart(
        charts.top_skills_chart(analytics.top_skills(candidates)),
        use_container_width=True,
    )

    row4 = st.columns(2)
    row4[0].plotly_chart(
        charts.location_distribution_chart(analytics.location_distribution(candidates)),
        use_container_width=True,
    )
    row4[1].plotly_chart(
        charts.company_distribution_chart(analytics.company_distribution(candidates)),
        use_container_width=True,
    )
