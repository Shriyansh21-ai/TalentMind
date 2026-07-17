"""Tests for the Enterprise Hiring Intelligence & Workforce Analytics (Phase 5 / M5).

Covers the analytics pipeline end-to-end — the score-free schema, the deterministic
composer, cohort distributions, executive KPIs, pipeline bottlenecks, team
analytics, trends, capacity, forecast, benchmarks and optimization (with and
without an injected analytics provider), safety/no-fabrication guarantees,
automatic registration and copilot delegation — all offline with synthetic
candidates.
"""

from __future__ import annotations

import json

import faiss  # noqa: F401  (faiss-before-torch load order)
from conftest import make_candidate

from src.ai.agents.hiring_intelligence import executive_metrics as kpi_mod
from src.ai.agents.hiring_intelligence import forecast as forecast_mod
from src.ai.agents.hiring_intelligence import optimization as optimization_mod
from src.ai.agents.hiring_intelligence import pipeline_analytics as pipeline_mod
from src.ai.agents.hiring_intelligence import team_analytics as team_mod
from src.ai.agents.hiring_intelligence import trend_analysis as trend_mod
from src.ai.agents.hiring_intelligence import validators
from src.ai.agents.hiring_intelligence.agent import (
    HiringIntelligenceInput,
    build_intelligence_evidence,
)
from src.ai.agents.hiring_intelligence.analytics_engine import (
    HiringIntelligenceEngine,
    build_cohort_snapshots,
    build_distributions,
    hiring_health_label,
    is_positive,
    role_family_of,
)
from src.ai.agents.hiring_intelligence.composer import compose_workforce_narrative
from src.ai.agents.hiring_intelligence.schemas import (
    HiringIntelligenceReport,
    WorkforceNarrative,
)
from src.ai.config.settings import AISettings
from src.ai.core.registry import registry
from src.ai.core.runner import AgentRunner
from src.ai.orchestration.registry.agent_registry import orchestration_registry
from src.ai.providers.composers import has_composer
from src.ai.validators.safety import SafetyGuard

JD = "Senior Machine Learning Engineer. Python, PyTorch, AWS. 8+ years."


class _AnalyticsProvider:
    """Injected analytics provider (supplies trends + team + capacity)."""

    def is_available(self) -> bool:
        return True

    def get_trends(self):
        return {
            "series": {
                "Hiring volume": {
                    "direction": "Up",
                    "evidence": "12mo series",
                    "confidence": 70,
                    "interpretation": "growing",
                }
            },
            "kpis": {"governance_health": 72.0, "compliance_readiness": 68.0},
            "bottlenecks": {
                "Approval delay": {
                    "severity": "High",
                    "cause": "slow sign-off",
                    "impact": "delayed starts",
                    "improvement": "SLA",
                }
            },
        }

    def get_team_metrics(self):
        return [
            {
                "dimension": "Department",
                "group": "Engineering",
                "count": 40,
                "hiring_health": "High",
                "detail": "warehouse",
            }
        ]

    def get_capacity(self):
        return {
            "Recruiter workload": {
                "level": "High",
                "risk": "overloaded",
                "recommendation": "add capacity",
            }
        }


def _runner() -> AgentRunner:
    return AgentRunner(settings=AISettings(provider="local", cache_enabled=False))


def _cohort(n: int = 5):
    titles = [
        "Senior ML Engineer",
        "Backend Engineer",
        "Data Scientist",
        "Engineering Manager",
        "Frontend Engineer",
    ]
    return [
        make_candidate(candidate_id=f"C{i}", title=titles[i % len(titles)], years=3 + i * 2)
        for i in range(n)
    ]


def _report(provider=None, **kw) -> HiringIntelligenceReport:
    engine = HiringIntelligenceEngine(ai_runner=_runner(), data_provider=provider)
    return engine.build(
        candidates=kw.pop("candidates", _cohort()),
        jd=kw.pop("jd", JD),
        generated_on="2026-07-16",
        **kw,
    )


def _snapshots(cohort):
    from src.insights.builder import build_insights

    return build_cohort_snapshots(cohort, JD, build_insights)


# ---------------------------------------------------------------------------
# Registration + schema
# ---------------------------------------------------------------------------


def test_agent_registered_with_ai_platform():
    assert registry.has("hiring_intelligence")


def test_composer_registered():
    assert has_composer(WorkforceNarrative.schema_name())


def test_agent_registered_with_orchestration():
    found = orchestration_registry.discover("hiring_intelligence")
    assert any(a.descriptor.name == "hiring_intelligence" for a in found)


def test_narrative_schema_is_score_free():
    SafetyGuard().assert_schema_is_score_free(WorkforceNarrative)


def test_tool_registered_in_builtin():
    import src.ai.tools.builtin  # noqa: F401
    from src.ai.tools.registry import registry as tool_registry

    assert tool_registry.has("hiring_intelligence")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_helpers():
    assert is_positive("Strong Hire") is True
    assert is_positive("No Hire") is False
    assert role_family_of("Senior ML Engineer") == "Data / ML"
    assert role_family_of("Backend Engineer") == "Engineering"
    assert hiring_health_label(1.0, 0.0) == "High"
    assert hiring_health_label(0.0, 1.0) == "Low"


def test_composer_never_empty_and_validates():
    out = compose_workforce_narrative({"analytics": {"cohort_size": 0, "data_available": False}})
    assert out["executive_summary"].strip()
    WorkforceNarrative(**out)


def test_build_evidence_shape():
    ev = build_intelligence_evidence(
        HiringIntelligenceInput(cohort_size=5, data_available=False, analytics={"kpis": []})
    )
    assert ev["cohort_size"] == 5
    assert "analytics" in ev


# ---------------------------------------------------------------------------
# Module 1 — distributions
# ---------------------------------------------------------------------------


def test_cohort_snapshots_and_distributions():
    snaps = _snapshots(_cohort(4))
    assert len(snaps) == 4
    for s in snaps:
        assert "recommendation" in s and "risk_level" in s and "role_family" in s
    dists = build_distributions(snaps)
    names = {d.name for d in dists}
    assert "Recommendation distribution" in names
    assert "Risk distribution" in names
    assert all(d.register == "Observed" for d in dists)
    assert sum(next(d for d in dists if d.name == "Risk distribution").counts.values()) == 4


# ---------------------------------------------------------------------------
# Module 5 — KPIs (evidence-backed; Unavailable without governance data)
# ---------------------------------------------------------------------------


def test_kpis_cohort_derivable_and_unavailable():
    snaps = _snapshots(_cohort(5))
    kpis = kpi_mod.build_kpis(snaps, None, False)
    by_name = {k.name: k for k in kpis}
    assert by_name["Hiring Health Index"].register == "Observed"
    assert by_name["Hiring Health Index"].value is not None
    # Governance-family KPIs need a data source -> Unavailable + null value.
    assert by_name["Governance Health"].register == "Unavailable"
    assert by_name["Governance Health"].value is None


def test_kpis_from_provider():
    snaps = _snapshots(_cohort(5))
    kpis = kpi_mod.build_kpis(snaps, _AnalyticsProvider(), True)
    by_name = {k.name: k for k in kpis}
    assert by_name["Governance Health"].register == "Observed"
    assert by_name["Governance Health"].value == 72.0


# ---------------------------------------------------------------------------
# Module 2 — bottlenecks
# ---------------------------------------------------------------------------


def test_bottlenecks_timed_unavailable_without_provider():
    snaps = _snapshots(_cohort(5))
    bottlenecks = pipeline_mod.build_bottlenecks(snaps, None, False)
    timed = [
        b
        for b in bottlenecks
        if b.stage in ("Screening delay", "Approval delay", "Offer delay", "Compliance delay")
    ]
    assert timed and all(b.register == "Unavailable" for b in timed)


def test_bottlenecks_observed_from_provider():
    snaps = _snapshots(_cohort(5))
    bottlenecks = pipeline_mod.build_bottlenecks(snaps, _AnalyticsProvider(), True)
    approval = [b for b in bottlenecks if b.stage == "Approval delay"][0]
    assert approval.register == "Observed"
    assert approval.severity == "High"


# ---------------------------------------------------------------------------
# Module 3 — team analytics
# ---------------------------------------------------------------------------


def test_team_analytics_observed_dimensions():
    snaps = _snapshots(_cohort(5))
    metrics = team_mod.build_team_metrics(snaps, None, False)
    observed = [m for m in metrics if m.register == "Observed"]
    unavailable = [m for m in metrics if m.register == "Unavailable"]
    assert any(m.dimension == "Role Family" for m in observed)
    assert any(m.dimension == "Location" for m in observed)
    # Department/BU/Hiring Manager/Recruiter unavailable without an org-structure source.
    assert {m.dimension for m in unavailable} == {
        "Department",
        "Business Unit",
        "Hiring Manager",
        "Recruiter",
    }


# ---------------------------------------------------------------------------
# Module 4 — trends (all Unavailable without provider)
# ---------------------------------------------------------------------------


def test_trends_unavailable_without_provider():
    trends = trend_mod.build_trends(_snapshots(_cohort(3)), None, False)
    assert trends and all(
        t.register == "Unavailable" and t.direction == "Unavailable" for t in trends
    )


def test_trends_observed_with_provider():
    trends = trend_mod.build_trends(_snapshots(_cohort(3)), _AnalyticsProvider(), True)
    volume = [t for t in trends if t.name == "Hiring volume"][0]
    assert volume.register == "Observed"
    assert volume.direction == "Up"


# ---------------------------------------------------------------------------
# Module 7 — forecast (never certain)
# ---------------------------------------------------------------------------


def test_forecast_scenarios_and_assumptions():
    forecast = forecast_mod.build_forecast(_snapshots(_cohort(4)), False)
    names = [f.name for f in forecast]
    assert names == ["Conservative", "Growth", "Aggressive"]
    for f in forecast:
        assert f.register == "Forecast"
        assert f.assumptions  # explicit assumptions, never certainty
        assert f.demand


# ---------------------------------------------------------------------------
# Module 9 — optimization (prioritized)
# ---------------------------------------------------------------------------


def test_optimization_prioritized_and_connect_provider():
    snaps = _snapshots(_cohort(5))
    kpis = kpi_mod.build_kpis(snaps, None, False)
    opts = optimization_mod.build_optimizations(snaps, kpis, False)
    assert opts
    # Without a provider, the "connect analytics" optimization fires.
    assert any(o.area == "Analytics" for o in opts)
    # Highest priority first.
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    priorities = [order.get(o.priority, 3) for o in opts]
    assert priorities == sorted(priorities)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def test_engine_produces_report_without_provider():
    report = _report()
    assert isinstance(report, HiringIntelligenceReport)
    assert report.cohort_size == 5
    assert report.data_available is False
    assert report.distributions and report.kpis and report.optimizations and report.forecast
    assert all(t.register == "Unavailable" for t in report.trends)
    assert report.narrative.executive_summary


def test_engine_with_provider_enables_trends_and_teams():
    report = _report(provider=_AnalyticsProvider(), candidates=_cohort(6))
    assert report.data_available is True
    assert any(t.register == "Observed" for t in report.trends)
    assert any(
        m.dimension == "Department" and m.register == "Observed" for m in report.team_metrics
    )


def test_engine_bounds_cohort():
    report = _report(candidates=_cohort(5), limit=3)
    assert report.cohort_size == 3


def test_engine_is_deterministic():
    r1 = _report(candidates=_cohort(4))
    r2 = _report(candidates=_cohort(4))
    assert [d.counts for d in r1.distributions] == [d.counts for d in r2.distributions]


def test_report_to_dict_is_serializable():
    assert json.dumps(_report().to_dict())
    assert json.dumps(_report(provider=_AnalyticsProvider()).to_dict())


def test_charts_present():
    report = _report()
    for key in (
        "distributions",
        "executive_kpis",
        "hiring_health",
        "pipeline_flow",
        "department_comparison",
        "forecast",
        "optimization_opportunities",
        "governance_health",
    ):
        assert key in report.charts


def test_never_ranks_individuals():
    # The report exposes aggregates only — no per-candidate ranking surface.
    report = _report()
    d = report.to_dict()
    assert "cohort_size" in d and "distributions" in d
    assert "candidate_ranking" not in d and "ranked_candidates" not in d


# ---------------------------------------------------------------------------
# Safety (Module 15)
# ---------------------------------------------------------------------------


def test_no_fabrication_unavailable_kpis_have_no_value():
    report = _report()
    warnings = validators.validate_safety(
        report.narrative, report.kpis, report.trends, report.data_available
    )
    assert all("flagged" not in w for w in warnings)
    for k in report.kpis:
        if k.register == "Unavailable":
            assert k.value is None


# ---------------------------------------------------------------------------
# Copilot integration (Module 12)
# ---------------------------------------------------------------------------


def test_copilot_routes_intelligence_questions():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    for message in [
        "How healthy is our hiring process?",
        "Show hiring analytics.",
        "What are our bottlenecks?",
        "Generate executive workforce report.",
        "Show hiring trends.",
        "Which departments need improvement?",
    ]:
        assert clf.classify(message, ConversationState()).intent == Intent.HIRING_INTELLIGENCE


def test_copilot_intelligence_intent_selects_tool():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.tool_selector import select_tools

    assert select_tools(Intent.HIRING_INTELLIGENCE) == ["hiring_intelligence"]


def test_copilot_existing_intents_unchanged():
    from src.ai.copilot.models import Intent
    from src.ai.copilot.planner import IntentClassifier
    from src.ai.copilot.state import ConversationState

    clf = IntentClassifier()
    cases = {
        "Why was this candidate hired?": Intent.HIRING_AUDIT,
        "Show audit trail": Intent.HIRING_COMPLIANCE,
        "Generate audit report": Intent.HIRING_AUDIT,
        "Is this hiring process compliant?": Intent.HIRING_COMPLIANCE,
        "Is this offer fair?": Intent.PAY_EQUITY,
        "Why are we offering this compensation?": Intent.COMPENSATION_GOVERNANCE,
        "Show me the dashboard distribution": Intent.DASHBOARD_QUESTION,
        "Generate executive report": Intent.EXECUTIVE_REPORT,
        "Run the hiring committee": Intent.HIRING_COMMITTEE,
    }
    for message, expected in cases.items():
        assert clf.classify(message, ConversationState()).intent == expected


def test_copilot_delegates_to_intelligence_end_to_end():
    from src.ai.copilot.controller import RecruiterCopilot
    from src.ai.copilot.models import Intent
    from src.ai.tools.provider import InMemoryCandidateRepository

    repo = InMemoryCandidateRepository(_cohort(5))
    cop = RecruiterCopilot(repo, ai_runner=_runner())
    turn = cop.ask("s1", "How healthy is our hiring process?", jd=JD)
    assert turn.status == "ok"
    assert turn.intent == Intent.HIRING_INTELLIGENCE
    assert "hiring_intelligence" in [t["name"] for t in turn.tools_used]
    assert "Hiring Intelligence" in turn.evidence_sources
    assert turn.answer
