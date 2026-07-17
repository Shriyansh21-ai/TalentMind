"""Smart-filtering engine (Module 6).

Evaluates :class:`FilterCriteria` against the shared :class:`CandidateInsights`
bundle (plus optional pipeline state) and composes cleanly with FAISS semantic
search: pass the ids returned by ``recruiter_search`` as ``allowed_ids`` and the
structured filters are applied *on top of* the semantic result set, so recruiters
can say "candidates semantically like X **and** senior **and** low-risk".

Pure and Streamlit-free.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from src.filtering.models import FilterCriteria
from src.insights.models import CandidateInsights
from src.pipeline.models import CandidatePipelineStatus


def _has_all_skills(insights: CandidateInsights, required: Sequence[str]) -> bool:
    """Return ``True`` iff the candidate's skills cover every required skill."""
    if not required:
        return True
    owned = {s.name.lower() for s in insights.candidate.skills}
    for wanted in required:
        needle = wanted.lower().strip()
        if not needle:
            continue
        if not any(needle in skill for skill in owned):
            return False
    return True


def _matches_stage(
    candidate_id: str,
    allowed_stages: Iterable[str],
    pipeline_states: dict[str, CandidatePipelineStatus] | None,
) -> bool:
    """Return ``True`` iff the candidate's pipeline stage is permitted.

    Candidates with no pipeline record are treated as ``Applied`` (their implicit
    entry stage) so stage filtering behaves intuitively before any workflow action.
    """
    allowed = set(allowed_stages)
    if not allowed:
        return True
    status = (pipeline_states or {}).get(candidate_id)
    current = status.current_stage.value if status else "Applied"
    return current in allowed


def matches(
    insights: CandidateInsights,
    criteria: FilterCriteria,
    pipeline_states: dict[str, CandidatePipelineStatus] | None = None,
) -> bool:
    """Return ``True`` iff ``insights`` satisfies every set constraint.

    Args:
        insights: The candidate's shared insight bundle.
        criteria: The recruiter filter to evaluate.
        pipeline_states: Optional pipeline-state map (needed only for the stage
            filter).

    Returns:
        Whether the candidate passes all active constraints.
    """
    intel = insights.intelligence

    if criteria.min_experience is not None and (
        insights.years_of_experience < criteria.min_experience
    ):
        return False
    if criteria.max_experience is not None and (
        insights.years_of_experience > criteria.max_experience
    ):
        return False

    if not _has_all_skills(insights, criteria.required_skills):
        return False

    if criteria.company and (criteria.company.lower() not in insights.company.lower()):
        return False
    if criteria.location and (criteria.location.lower() not in insights.location.lower()):
        return False

    if criteria.allowed_risk_levels and (
        insights.risk.risk_level not in criteria.allowed_risk_levels
    ):
        return False

    if criteria.allowed_recommendations and (
        intel.recommendation not in criteria.allowed_recommendations
    ):
        return False

    if not _matches_stage(insights.candidate_id, criteria.allowed_stages, pipeline_states):
        return False

    if criteria.min_timeline_score is not None and (
        insights.timeline.timeline_score < criteria.min_timeline_score
    ):
        return False
    if criteria.min_technical_score is not None and (
        intel.technical_score < criteria.min_technical_score
    ):
        return False
    if criteria.min_leadership_score is not None and (
        intel.leadership_score < criteria.min_leadership_score
    ):
        return False
    if criteria.min_career_growth is not None and (
        intel.career_growth_score < criteria.min_career_growth
    ):
        return False
    if criteria.min_learning_velocity is not None and (
        intel.learning_velocity < criteria.min_learning_velocity
    ):
        return False
    if criteria.min_skill_match is not None and (
        insights.skill_match_percent < criteria.min_skill_match
    ):
        return False

    return True


def apply_filters(
    insights_list: Sequence[CandidateInsights],
    criteria: FilterCriteria,
    pipeline_states: dict[str, CandidatePipelineStatus] | None = None,
    allowed_ids: Iterable[str] | None = None,
) -> list[CandidateInsights]:
    """Filter an insight cohort by ``criteria``, optionally within a FAISS subset.

    Args:
        insights_list: Candidate insight bundles to filter.
        criteria: The recruiter filter.
        pipeline_states: Optional pipeline-state map for the stage filter.
        allowed_ids: When provided (e.g. FAISS search hits), only candidates whose
            id is in this set are considered — this is the composition seam that
            lets structured filtering run on top of semantic search results.

    Returns:
        The matching insight bundles, in input order.
    """
    id_gate = set(allowed_ids) if allowed_ids is not None else None
    result: list[CandidateInsights] = []
    for insights in insights_list:
        if id_gate is not None and insights.candidate_id not in id_gate:
            continue
        if matches(insights, criteria, pipeline_states):
            result.append(insights)
    return result
