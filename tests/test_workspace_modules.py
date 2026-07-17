"""Tests for the insight-backed workspace modules.

Covers Module 2 (comparison), Module 3 (talent pool), Module 4 (interview),
Module 5 (dashboard analytics + charts) and Module 6 (filtering) using synthetic
candidates so no ML dependency or production data is required.
"""

from __future__ import annotations

import faiss  # noqa: F401  (import-order safety; harmless in tests)
from conftest import make_candidate

from src.comparison.builder import MAX_COMPARISON, build_comparison
from src.comparison.models import NUMERIC_METRICS
from src.dashboard import analytics, charts
from src.filtering.engine import apply_filters, matches
from src.filtering.models import FilterCriteria
from src.insights.builder import build_insights
from src.insights.models import CandidateInsights
from src.interview.planner import build_interview_plan
from src.talent_pool.models import TalentPool
from src.talent_pool.segmentation import (
    filter_by_pool,
    pool_counts,
    segment_candidate,
    segment_pool,
)

JD = "python machine learning llm aws docker rag pytorch"


def _insights(**kwargs) -> CandidateInsights:
    return build_insights(make_candidate(**kwargs), jd=JD, match_score=150.0)


# ---------------------------------------------------------------------------
# Module 2 — Comparison
# ---------------------------------------------------------------------------


def test_comparison_builds_rows():
    a = _insights(candidate_id="A", title="ML Engineer")
    b = _insights(candidate_id="B", title="Backend Engineer", years=3.0)
    report = build_comparison([a, b])
    assert report.candidate_ids == ["A", "B"]
    assert set(report.best_by_metric.keys()) == set(NUMERIC_METRICS.keys())
    for winner in report.best_by_metric.values():
        assert winner in {"A", "B"}


def test_comparison_caps_at_five():
    people = [_insights(candidate_id=f"C{i}") for i in range(7)]
    report = build_comparison(people)
    assert len(report.rows) == MAX_COMPARISON


def test_comparison_empty():
    report = build_comparison([])
    assert report.rows == []
    assert report.best_by_metric == {}


def test_comparison_risk_lower_is_better():
    # risk_score is the sole lower-is-better metric.
    low = _insights(candidate_id="LOW", years=9.0)
    high = _insights(candidate_id="HIGH", years=0.5, endorsements=0, skills=["Python"])
    report = build_comparison([low, high])
    winner_id = report.best_by_metric["risk_score"]
    rows = {r.candidate_id: r for r in report.rows}
    assert rows[winner_id].risk_score == min(r.risk_score for r in report.rows)


# ---------------------------------------------------------------------------
# Module 3 — Talent Pool
# ---------------------------------------------------------------------------


def test_segment_returns_pools():
    ins = _insights(title="Senior Machine Learning Engineer")
    assignment = segment_candidate(ins)
    # Senior (9 yrs) + ML title/skills should yield at least these pools.
    assert TalentPool.SENIOR_ENGINEERING in assignment.pools
    assert TalentPool.ML_SPECIALISTS in assignment.pools
    assert len(assignment.rationale) == len(assignment.pools)


def test_future_pipeline_for_junior():
    ins = _insights(candidate_id="JR", years=1.5)
    assignment = segment_candidate(ins)
    assert TalentPool.FUTURE_PIPELINE in assignment.pools
    assert TalentPool.SENIOR_ENGINEERING not in assignment.pools


def test_domain_pools_backend_frontend():
    be = segment_candidate(
        _insights(title="Backend Engineer", skills=["Java", "Spring", "Microservices"])
    )
    fe = segment_candidate(
        _insights(title="Frontend Engineer", skills=["React", "TypeScript", "CSS"])
    )
    assert TalentPool.BACKEND in be.pools
    assert TalentPool.FRONTEND in fe.pools


def test_segment_pool_and_filter():
    people = [
        _insights(candidate_id="ML1", title="ML Engineer", skills=["Python", "PyTorch", "LLM"]),
        _insights(candidate_id="FE1", title="Frontend Engineer", skills=["React", "CSS"]),
    ]
    assignments = segment_pool(people)
    ml_ids = filter_by_pool(assignments, TalentPool.ML_SPECIALISTS)
    assert "ML1" in ml_ids
    assert "FE1" not in ml_ids

    counts = pool_counts(assignments)
    assert counts[TalentPool.ML_SPECIALISTS.value] >= 1
    assert set(counts.keys()) == {p.value for p in TalentPool}


# ---------------------------------------------------------------------------
# Module 4 — Interview Intelligence
# ---------------------------------------------------------------------------


def test_interview_plan_populated():
    plan = build_interview_plan(_insights())
    assert plan.technical_topics
    assert plan.system_design_topics
    assert plan.behavioral_questions
    assert plan.leadership_questions
    assert plan.validation_questions
    assert plan.deep_dive_topics
    assert plan.coding_focus
    assert plan.communication_focus
    assert plan.risk_followups


def test_interview_plan_deterministic():
    ins = _insights()
    assert build_interview_plan(ins) == build_interview_plan(ins)


def test_interview_seniority_scales_system_design():
    senior = build_interview_plan(_insights(years=12.0))
    junior = build_interview_plan(_insights(years=1.0))
    assert len(senior.system_design_topics) >= len(junior.system_design_topics)


# ---------------------------------------------------------------------------
# Module 5 — Dashboard analytics + charts
# ---------------------------------------------------------------------------


def test_analytics_field_aggregations():
    cands = [
        make_candidate(candidate_id="A", location="Bangalore", company="Acme"),
        make_candidate(candidate_id="B", location="Bangalore", company="Globex"),
    ]
    assert analytics.experience_distribution(cands) == [9.0, 9.0]
    locs = dict(analytics.location_distribution(cands))
    assert locs["Bangalore"] == 2
    comps = dict(analytics.company_distribution(cands))
    assert comps["Acme"] == 1 and comps["Globex"] == 1
    skills = dict(analytics.top_skills(cands))
    assert skills.get("Python") == 2


def test_analytics_engine_aggregations():
    ins = [_insights(candidate_id="A"), _insights(candidate_id="B")]
    assert len(analytics.score_distribution(ins)) == 2
    risk = analytics.risk_distribution(ins)
    assert set(risk.keys()) >= {"Low", "Medium", "High"}
    rec = analytics.recommendation_distribution(ins)
    assert sum(rec.values()) == 2


def test_charts_return_figures():
    ins = [_insights(candidate_id="A"), _insights(candidate_id="B")]
    cands = [make_candidate(candidate_id="A"), make_candidate(candidate_id="B")]
    figs = [
        charts.risk_distribution_chart(analytics.risk_distribution(ins)),
        charts.score_distribution_chart(analytics.score_distribution(ins)),
        charts.experience_distribution_chart(analytics.experience_distribution(cands)),
        charts.top_skills_chart(analytics.top_skills(cands)),
        charts.location_distribution_chart(analytics.location_distribution(cands)),
        charts.company_distribution_chart(analytics.company_distribution(cands)),
        charts.recommendation_distribution_chart(analytics.recommendation_distribution(ins)),
        charts.stage_distribution_chart({"Applied": 1}),
        charts.pipeline_chart({"Applied": 1}),
        charts.hiring_funnel([("Applied", 2), ("Shortlisted", 1)]),
    ]
    for fig in figs:
        assert fig is not None
        assert hasattr(fig, "to_dict")


def test_charts_handle_empty():
    assert charts.risk_distribution_chart({}) is not None
    assert charts.hiring_funnel([]) is not None
    assert charts.top_skills_chart([]) is not None


# ---------------------------------------------------------------------------
# Module 6 — Smart Filtering
# ---------------------------------------------------------------------------


def test_filter_by_experience():
    people = [
        _insights(candidate_id="SR", years=10.0),
        _insights(candidate_id="JR", years=1.0),
    ]
    result = apply_filters(people, FilterCriteria(min_experience=5.0))
    ids = [i.candidate_id for i in result]
    assert ids == ["SR"]


def test_filter_by_required_skills():
    people = [
        _insights(candidate_id="ML", skills=["Python", "PyTorch", "LLM"]),
        _insights(candidate_id="FE", skills=["React", "CSS"]),
    ]
    result = apply_filters(people, FilterCriteria(required_skills=["pytorch"]))
    assert [i.candidate_id for i in result] == ["ML"]


def test_filter_composes_with_faiss_allowed_ids():
    people = [
        _insights(candidate_id="A", years=10.0),
        _insights(candidate_id="B", years=10.0),
    ]
    # Even though both match the criteria, only FAISS-approved ids survive.
    result = apply_filters(people, FilterCriteria(min_experience=1.0), allowed_ids={"B"})
    assert [i.candidate_id for i in result] == ["B"]


def test_filter_by_location_and_company():
    people = [
        _insights(candidate_id="A", location="Bangalore", company="Acme AI"),
        _insights(candidate_id="B", location="Delhi", company="Globex"),
    ]
    assert [
        i.candidate_id for i in apply_filters(people, FilterCriteria(location="bangalore"))
    ] == ["A"]
    assert [i.candidate_id for i in apply_filters(people, FilterCriteria(company="globex"))] == [
        "B"
    ]


def test_empty_criteria_passes_all():
    people = [_insights(candidate_id="A"), _insights(candidate_id="B")]
    assert FilterCriteria().is_empty()
    assert len(apply_filters(people, FilterCriteria())) == 2


def test_matches_stage_defaults_to_applied():
    ins = _insights(candidate_id="A")
    assert matches(ins, FilterCriteria(allowed_stages={"Applied"}))
    assert not matches(ins, FilterCriteria(allowed_stages={"Offer"}))
