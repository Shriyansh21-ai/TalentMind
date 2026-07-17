"""Smart Filtering UI (Module 6 UI).

Renders the recruiter filter panel, assembles a :class:`FilterCriteria`, and
applies it to the insight cohort. An optional semantic query is run through the
FAISS-backed recruiter search and used as an id gate, so structured filters and
semantic search compose: "candidates like <query> AND senior AND low-risk".
"""

from __future__ import annotations

from collections.abc import Sequence

import streamlit as st

from src.filtering.engine import apply_filters
from src.filtering.models import FilterCriteria
from src.insights.models import CandidateInsights
from src.pipeline.models import CandidatePipelineStatus, PipelineStage

_RISK_LEVELS = ["Low", "Medium", "High"]
_RECOMMENDATIONS = ["Strong Hire", "Hire", "Hold", "Reject"]
_STAGES = [s.value for s in PipelineStage]

# How many FAISS neighbours to consider when a semantic query is supplied.
_FAISS_POOL = 200


def render_smart_filters(
    insights: Sequence[CandidateInsights],
    pipeline_states: dict[str, CandidatePipelineStatus],
) -> None:
    """Render the smart-filter panel and the filtered result list.

    Args:
        insights: The bounded insight cohort to filter.
        pipeline_states: Pipeline state map (for the stage filter).
    """
    st.subheader("Smart Filters")

    if not insights:
        st.info("No candidates available to filter.")
        return

    criteria, semantic_query = _render_controls()

    allowed_ids: set | None = None
    if semantic_query:
        allowed_ids = _semantic_gate(semantic_query)
        if allowed_ids is None:
            st.warning("Semantic search unavailable — showing structured filters only.")

    filtered = apply_filters(
        insights, criteria, pipeline_states=pipeline_states, allowed_ids=allowed_ids
    )

    st.caption(f"{len(filtered)} of {len(insights)} candidates match your filters.")
    _render_results(filtered)


def _render_controls():
    """Render filter widgets and return ``(FilterCriteria, semantic_query)``."""
    semantic_query = st.text_input(
        "Semantic query (optional, composes with filters via FAISS)",
        placeholder="e.g. LLM engineer with RAG and vector-search experience",
        key="filter_semantic_query",
    )

    row1 = st.columns(3)
    min_exp = row1[0].number_input("Min experience (yrs)", 0.0, 40.0, 0.0, 0.5, key="f_minexp")
    max_exp = row1[1].number_input("Max experience (yrs)", 0.0, 40.0, 40.0, 0.5, key="f_maxexp")
    min_match = row1[2].slider("Min skill match %", 0, 100, 0, key="f_match")

    row2 = st.columns(3)
    min_tech = row2[0].slider("Min technical", 0, 100, 0, key="f_tech")
    min_lead = row2[1].slider("Min leadership", 0, 100, 0, key="f_lead")
    min_timeline = row2[2].slider("Min timeline", 0, 100, 0, key="f_timeline")

    row3 = st.columns(3)
    min_growth = row3[0].slider("Min career growth", 0, 100, 0, key="f_growth")
    min_learning = row3[1].slider("Min learning velocity", 0, 100, 0, key="f_learn")
    skills_raw = row3[2].text_input("Required skills (comma-sep)", key="f_skills")

    row4 = st.columns(2)
    company = row4[0].text_input("Company contains", key="f_company")
    location = row4[1].text_input("Location contains", key="f_location")

    row5 = st.columns(3)
    risk_levels = row5[0].multiselect("Risk level", _RISK_LEVELS, key="f_risk")
    recommendations = row5[1].multiselect("Recommendation", _RECOMMENDATIONS, key="f_rec")
    stages = row5[2].multiselect("Pipeline stage", _STAGES, key="f_stage")

    required_skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

    criteria = FilterCriteria(
        min_experience=min_exp if min_exp > 0 else None,
        max_experience=max_exp if max_exp < 40.0 else None,
        required_skills=required_skills,
        company=company.strip() or None,
        location=location.strip() or None,
        allowed_risk_levels=set(risk_levels),
        allowed_recommendations=set(recommendations),
        allowed_stages=set(stages),
        min_timeline_score=float(min_timeline) if min_timeline > 0 else None,
        min_technical_score=float(min_tech) if min_tech > 0 else None,
        min_leadership_score=float(min_lead) if min_lead > 0 else None,
        min_career_growth=float(min_growth) if min_growth > 0 else None,
        min_learning_velocity=float(min_learning) if min_learning > 0 else None,
        min_skill_match=float(min_match) if min_match > 0 else None,
    )
    return criteria, semantic_query.strip()


def _semantic_gate(query: str) -> set | None:
    """Return the candidate ids returned by FAISS for ``query`` (or ``None``).

    The FAISS-backed search (and its heavy torch / sentence-transformers
    dependency) is imported lazily here so the workspace only pulls in the ML
    stack when a recruiter actually runs a semantic query — the structured
    filters work without it.
    """
    try:
        from src.semantic.recruiter_search import recruiter_search

        hits = recruiter_search(query, top_k=_FAISS_POOL)
    except Exception:
        return None
    return {candidate.candidate_id for candidate, _ in hits}


def _render_results(filtered: list[CandidateInsights]) -> None:
    """Render a compact list of the filtered candidates."""
    if not filtered:
        st.caption("No candidates match — try relaxing the filters.")
        return

    for insight in filtered[:25]:
        with st.expander(f"{insight.title} · {insight.company} ({insight.candidate_id})"):
            cols = st.columns(4)
            cols[0].metric("Overall", f"{insight.intelligence.overall_score:.0f}")
            cols[1].metric("Technical", f"{insight.intelligence.technical_score:.0f}")
            cols[2].metric("Risk", insight.risk.risk_level)
            cols[3].metric("Match", f"{insight.skill_match_percent:.0f}%")
            st.caption(
                f"{insight.years_of_experience:.1f} yrs · {insight.location} · "
                f"{insight.intelligence.recommendation}"
            )
