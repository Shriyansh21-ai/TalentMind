"""Builder for the Candidate Comparison Workspace (Module 2).

Turns a list of shared :class:`CandidateInsights` bundles into a
:class:`ComparisonReport`. Pure and Streamlit-free so it can be unit-tested; the
UI layer supplies the (cached) insight bundles.
"""

from __future__ import annotations

from collections.abc import Sequence

from src.comparison.models import (
    NUMERIC_METRICS,
    ComparisonReport,
    ComparisonRow,
)
from src.insights.models import CandidateInsights

# Product cap: a comparison view stays readable up to five candidates.
MAX_COMPARISON = 5


def _to_row(insights: CandidateInsights) -> ComparisonRow:
    """Project one insight bundle onto a flat :class:`ComparisonRow`."""
    intel = insights.intelligence
    recommendation = insights.recommendation

    return ComparisonRow(
        candidate_id=insights.candidate_id,
        title=insights.title,
        company=insights.company,
        overall_score=intel.overall_score,
        hiring_recommendation=(
            recommendation.recommendation if recommendation else intel.recommendation
        ),
        timeline_score=insights.timeline.timeline_score,
        risk_score=insights.risk.risk_score,
        risk_level=insights.risk.risk_level,
        technical_score=intel.technical_score,
        leadership_score=intel.leadership_score,
        experience_score=intel.experience_score,
        career_growth=intel.career_growth_score,
        skill_match=insights.skill_match_percent,
        strengths=list(intel.strengths),
        weaknesses=list(intel.weaknesses),
        recruiter_summary=list(insights.summary),
        interview_focus=(list(recommendation.interview_focus) if recommendation else []),
        missing_skills=insights.missing_skills,
    )


def _best_by_metric(rows: list[ComparisonRow]) -> dict:
    """Return ``{metric: winning_candidate_id}`` across the numeric metrics."""
    winners: dict = {}
    for metric, higher_is_better in NUMERIC_METRICS.items():
        best_row = None
        best_value = None
        for row in rows:
            value = getattr(row, metric)
            if best_value is None or (
                value > best_value if higher_is_better else value < best_value
            ):
                best_value = value
                best_row = row
        if best_row is not None:
            winners[metric] = best_row.candidate_id
    return winners


def build_comparison(
    insights_list: Sequence[CandidateInsights],
) -> ComparisonReport:
    """Build a :class:`ComparisonReport` from up to :data:`MAX_COMPARISON` bundles.

    Args:
        insights_list: Insight bundles for the candidates to compare. Only the
            first :data:`MAX_COMPARISON` are used (extras are ignored so the view
            never overflows).

    Returns:
        A populated :class:`ComparisonReport`; empty input yields an empty report.
    """
    selected = list(insights_list)[:MAX_COMPARISON]
    rows = [_to_row(insights) for insights in selected]
    return ComparisonReport(rows=rows, best_by_metric=_best_by_metric(rows))
