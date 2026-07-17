"""Pure analytics aggregations for the Recruiter Dashboard (Module 5).

These functions turn raw candidates, shared insight bundles and pipeline state
into small, chart-ready data structures (counts / ordered pairs / value lists).
They contain no plotting and no Streamlit — the plotting lives in
``src/dashboard/charts.py`` and the wiring in ``src/ui/analytics_dashboard.py``.

Cheap, field-only aggregations (experience, skills, location, company) operate on
the full candidate pool. Aggregations that require engine output (score, risk,
recommendation) operate on the caller-supplied insight cohort so the dashboard
never triggers intelligence computation for the entire database.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from src.insights.models import CandidateInsights
from src.models.candidates import Candidate
from src.pipeline.models import CandidatePipelineStatus, PipelineStage

CountPairs = list[tuple[str, int]]

# Canonical funnel order for the hiring-funnel chart (active stages only).
_FUNNEL_STAGES: list[PipelineStage] = [
    PipelineStage.APPLIED,
    PipelineStage.SHORTLISTED,
    PipelineStage.RECRUITER_REVIEW,
    PipelineStage.TECHNICAL_INTERVIEW,
    PipelineStage.HIRING_MANAGER,
    PipelineStage.HR_INTERVIEW,
    PipelineStage.OFFER,
    PipelineStage.OFFER_ACCEPTED,
]


# ---------------------------------------------------------------------------
# Field-only aggregations (full candidate pool)
# ---------------------------------------------------------------------------


def experience_distribution(candidates: Sequence[Candidate]) -> list[float]:
    """Return the years-of-experience for every candidate (histogram input)."""
    return [c.profile.years_of_experience for c in candidates]


def top_skills(candidates: Sequence[Candidate], limit: int = 15) -> CountPairs:
    """Return the ``limit`` most common skills as ``(skill, count)`` pairs."""
    counter: Counter = Counter()
    for candidate in candidates:
        for skill in candidate.skills:
            if skill.name:
                counter[skill.name] += 1
    return counter.most_common(limit)


def location_distribution(candidates: Sequence[Candidate], limit: int = 12) -> CountPairs:
    """Return the ``limit`` most common candidate locations."""
    counter: Counter = Counter(c.profile.location for c in candidates if c.profile.location)
    return counter.most_common(limit)


def company_distribution(candidates: Sequence[Candidate], limit: int = 12) -> CountPairs:
    """Return the ``limit`` most common current employers."""
    counter: Counter = Counter(
        c.profile.current_company for c in candidates if c.profile.current_company
    )
    return counter.most_common(limit)


# ---------------------------------------------------------------------------
# Engine-backed aggregations (bounded insight cohort)
# ---------------------------------------------------------------------------


def score_distribution(insights: Sequence[CandidateInsights]) -> list[float]:
    """Return overall intelligence scores for the cohort (histogram input)."""
    return [i.intelligence.overall_score for i in insights]


def risk_distribution(insights: Sequence[CandidateInsights]) -> dict[str, int]:
    """Return ``{risk_level: count}`` ordered Low / Medium / High."""
    counts = {"Low": 0, "Medium": 0, "High": 0}
    for item in insights:
        level = item.risk.risk_level
        counts[level] = counts.get(level, 0) + 1
    return counts


def recommendation_distribution(
    insights: Sequence[CandidateInsights],
) -> dict[str, int]:
    """Return ``{recommendation_label: count}`` from the intelligence engine."""
    counter: Counter = Counter(i.intelligence.recommendation for i in insights)
    return dict(counter)


# ---------------------------------------------------------------------------
# Pipeline aggregations (recruiter workflow state)
# ---------------------------------------------------------------------------


def stage_distribution(
    states: Sequence[CandidatePipelineStatus],
) -> dict[str, int]:
    """Return ``{stage_value: count}`` across every pipeline stage (0s included)."""
    counts: dict[str, int] = {stage.value: 0 for stage in PipelineStage}
    for status in states:
        counts[status.current_stage.value] = counts.get(status.current_stage.value, 0) + 1
    return counts


def funnel_counts(states: Sequence[CandidatePipelineStatus]) -> CountPairs:
    """Return cumulative funnel ``(stage, reached_count)`` pairs in funnel order.

    A candidate currently at stage *N* has, by definition, passed through every
    prior active stage, so the funnel shows how many candidates *reached at least*
    each stage — the shape recruiters expect from a hiring funnel.
    """
    stage_counts = stage_distribution(states)
    order_index = {stage: idx for idx, stage in enumerate(_FUNNEL_STAGES)}

    reached: list[tuple[str, int]] = []
    for idx, stage in enumerate(_FUNNEL_STAGES):
        total = 0
        for status in states:
            current = status.current_stage
            # Rejected/Hold candidates count toward every stage they had reached
            # before parking; approximate by their max reached stage in history.
            reached_idx = _max_reached_index(status, order_index)
            if reached_idx is not None and reached_idx >= idx:
                total += 1
        reached.append((stage.value, total))
    # ``stage_counts`` is retained for callers that want the raw (non-cumulative)
    # snapshot; unused here but computed once to keep a single aggregation path.
    del stage_counts
    return reached


def _max_reached_index(
    status: CandidatePipelineStatus, order_index: dict[PipelineStage, int]
) -> int | None:
    """Return the furthest active-funnel index this candidate ever reached."""
    best: int | None = None
    # Current stage (if active) counts.
    if status.current_stage in order_index:
        best = order_index[status.current_stage]
    # Otherwise scan history for the furthest active stage they passed through.
    for event in status.stage_history:
        try:
            stage = PipelineStage.from_value(event.to_stage)
        except ValueError:
            continue
        if stage in order_index:
            idx = order_index[stage]
            best = idx if best is None else max(best, idx)
    return best
