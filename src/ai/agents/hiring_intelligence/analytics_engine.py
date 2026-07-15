"""HiringIntelligenceEngine — cohort analytics collector (Modules 1, 13, 14).

Builds a bounded **cohort snapshot** from the platform's existing per-candidate
intelligence (the cheap, cached ``insights_fn`` — intelligence / risk /
recommendation / timeline), aggregates it into observed distributions (Module 1),
then orchestrates the pipeline / team / trend / KPI / capacity / forecast /
benchmark / optimization modules and assembles the unified
:class:`HiringIntelligenceReport`.

It provides **strategic organizational intelligence — never candidate ranking**.
Org-wide event history is not persisted by the platform, so metrics that need it
(trends, delays, team breakdowns, capacity) are reported **Unavailable** unless a
:class:`WorkforceDataProvider` is injected (Module 13). Nothing is fabricated
(Module 15). All collaborators are injected (SOLID / DI).

Shared pure helpers (``hiring_health_label``, ``share``, ``is_positive``,
``role_family_of``) live here so the leaf analytics modules reuse them without
duplication; the engine imports the leaf modules lazily to avoid an import cycle.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from src.ai.core.runner import AgentRunner

from src.ai.agents.hiring_intelligence.agent import (
    HiringIntelligenceInput,
    build_intelligence_evidence,
    hiring_intelligence_agent,
)
from src.ai.agents.hiring_intelligence.composer import compose_workforce_narrative
from src.ai.agents.hiring_intelligence.schemas import (
    Distribution,
    HiringIntelligenceReport,
    WorkforceNarrative,
)
from src.ai.agents.hiring_intelligence.templates import ANALYTICS_COHORT


# ---------------------------------------------------------------------------
# Module 13 — future analytics-data provider interface (interface only)
# ---------------------------------------------------------------------------


@runtime_checkable
class WorkforceDataProvider(Protocol):
    """Future analytics integration seam (Module 13 — interface only).

    A real implementation (HR data warehouse, people-analytics, Snowflake,
    BigQuery, Databricks, Synapse, Power BI, Tableau) serves the org-wide hiring
    event history + team structure that TalentMind does not itself persist.
    TalentMind implements none of these; the Protocol exists so a later milestone
    plugs one in without a redesign.
    """

    def is_available(self) -> bool:
        """Return True when live workforce analytics data can be served."""
        ...

    def get_trends(self) -> Optional[Dict[str, Any]]:
        """Return historical trend series or ``None``."""
        ...

    def get_team_metrics(self) -> Optional[List[Dict[str, Any]]]:
        """Return team/department/BU aggregates or ``None``."""
        ...

    def get_capacity(self) -> Optional[Dict[str, Any]]:
        """Return recruiter/interviewer capacity data or ``None``."""
        ...


class NullWorkforceDataProvider:
    """Default provider: no analytics warehouse (the shipped behaviour)."""

    def is_available(self) -> bool:
        """Always False — no analytics source is connected."""
        return False

    def get_trends(self) -> Optional[Dict[str, Any]]:
        """Return ``None`` — no trend data available."""
        return None

    def get_team_metrics(self) -> Optional[List[Dict[str, Any]]]:
        """Return ``None`` — no team data available."""
        return None

    def get_capacity(self) -> Optional[Dict[str, Any]]:
        """Return ``None`` — no capacity data available."""
        return None


# ---------------------------------------------------------------------------
# Shared pure helpers (reused by the leaf analytics modules)
# ---------------------------------------------------------------------------

_POSITIVE = ("strong hire", "hire", "strong fit", "good fit", "lean hire", "recommend")
_NEGATIVE = ("no hire", "not recommended", "weak", "reject")


def is_positive(recommendation: str) -> bool:
    """Return True when a recommendation label is a positive (hire) signal."""
    r = (recommendation or "").strip().lower()
    if any(n in r for n in _NEGATIVE):
        return False
    return any(p in r for p in _POSITIVE)


def share(items: List[Any], predicate) -> float:
    """Return the 0-1 share of ``items`` satisfying ``predicate`` (0 if empty)."""
    if not items:
        return 0.0
    return sum(1 for i in items if predicate(i)) / len(items)


def hiring_health_label(hire_share: float, high_risk_share: float) -> str:
    """Map a hire share + high-risk share to a qualitative hiring-health band."""
    score = hire_share * 100.0 - high_risk_share * 50.0
    if score >= 55:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


_ROLE_FAMILY_HINTS = [
    ("Data / ML", ("machine learning", "ml engineer", "data scientist", "data engineer", "ai ", "mlops")),
    ("Engineering", ("engineer", "developer", "sde", "backend", "frontend", "full stack", "devops", "sre", "architect")),
    ("Product", ("product manager", "product owner", "program manager")),
    ("Design", ("designer", "ux", "ui ")),
    ("Management", ("manager", "director", "head of", "vp ", "lead")),
]


def role_family_of(title: str) -> str:
    """Map a job title to a coarse role family (Observed from the profile)."""
    t = (title or "").lower()
    for family, hints in _ROLE_FAMILY_HINTS:
        if any(h in t for h in hints):
            return family
    return "Other"


# ---------------------------------------------------------------------------
# Cohort snapshot (Observed per-candidate intelligence, aggregated)
# ---------------------------------------------------------------------------


def _num(obj: Any, attr: str, default: float = 0.0) -> float:
    try:
        return float(getattr(obj, attr, default) or default)
    except (TypeError, ValueError):
        return default


def build_cohort_snapshots(candidates: List[Any], jd: str, insights_fn: Any) -> List[Dict[str, Any]]:
    """Build per-candidate Observed snapshots from the cached insight engines."""
    if insights_fn is None:
        from src.insights.builder import build_insights

        insights_fn = build_insights

    snapshots: List[Dict[str, Any]] = []
    for candidate in candidates:
        try:
            insights = insights_fn(candidate, jd)
        except Exception:  # a candidate that cannot be analysed is skipped, not faked
            continue
        intelligence = getattr(insights, "intelligence", None)
        risk = getattr(insights, "risk", None)
        recommendation = getattr(insights, "recommendation", None)
        profile = getattr(candidate, "profile", None)

        rec_label = (
            getattr(recommendation, "recommendation", "")
            or getattr(intelligence, "recommendation", "")
            or "Unknown"
        )
        overall = _num(intelligence, "overall_score")
        risk_level = str(getattr(risk, "risk_level", "Unknown") or "Unknown")
        snapshots.append(
            {
                "candidate_id": getattr(candidate, "candidate_id", ""),
                "recommendation": rec_label,
                "risk_level": risk_level,
                "risk_score": _num(risk, "risk_score"),
                "overall": overall,
                "technical": _num(intelligence, "technical_score"),
                "leadership": _num(intelligence, "leadership_score"),
                "confidence": _num(intelligence, "confidence"),
                "interview_ready": overall >= 55.0 and risk_level != "High",
                "location": getattr(profile, "location", "") or "Unknown",
                "role_family": role_family_of(getattr(profile, "current_title", "")),
            }
        )
    return snapshots


def build_distributions(cohort: List[Dict[str, Any]]) -> List[Distribution]:
    """Build the Module 1 observed distributions over the analyzed cohort."""
    total = len(cohort)

    def _dist(name: str, key: str, note: str = "") -> Distribution:
        counts: Dict[str, int] = {}
        for s in cohort:
            counts[str(s.get(key, "Unknown"))] = counts.get(str(s.get(key, "Unknown")), 0) + 1
        return Distribution(name=name, counts=counts, total=total, register="Observed", note=note)

    recommendation = _dist("Recommendation distribution", "recommendation", "Offer/recommendation mix across the analyzed cohort.")
    risk = _dist("Risk distribution", "risk_level")
    role_family = _dist("Role-family distribution", "role_family")

    interview_counts = {"Ready": 0, "Not ready": 0}
    for s in cohort:
        interview_counts["Ready" if s.get("interview_ready") else "Not ready"] += 1
    interview = Distribution(
        name="Interview-readiness distribution", counts=interview_counts, total=total,
        register="Observed", note="Cohort interview-readiness proxy from capability + risk.",
    )
    return [recommendation, risk, role_family, interview]


class HiringIntelligenceEngine:
    """Builds a unified :class:`HiringIntelligenceReport` from a cohort's intelligence."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: Optional[AgentRunner] = None,
        insights_fn: Optional[Any] = None,
        data_provider: Optional[WorkforceDataProvider] = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.data_provider = data_provider or NullWorkforceDataProvider()

    # -- public API ---------------------------------------------------------

    def build(
        self,
        candidates: Optional[List[Any]] = None,
        *,
        repository: Any = None,
        jd: str = "",
        limit: int = ANALYTICS_COHORT,
        generated_on: str = "",
    ) -> HiringIntelligenceReport:
        """Analyze a cohort and assemble the workforce-intelligence report."""
        if candidates is None:
            if repository is None:
                raise ValueError("Provide candidates, or a repository.")
            candidates = repository.sample(limit=limit)
        candidates = list(candidates)[:limit]

        # Lazy imports break the helper import cycle (leaf modules import helpers here).
        from src.ai.agents.hiring_intelligence import benchmark as benchmark_mod
        from src.ai.agents.hiring_intelligence import capacity as capacity_mod
        from src.ai.agents.hiring_intelligence import charts as charts_mod
        from src.ai.agents.hiring_intelligence import executive_metrics as kpi_mod
        from src.ai.agents.hiring_intelligence import forecast as forecast_mod
        from src.ai.agents.hiring_intelligence import insights as insights_mod
        from src.ai.agents.hiring_intelligence import optimization as optimization_mod
        from src.ai.agents.hiring_intelligence import pipeline_analytics as pipeline_mod
        from src.ai.agents.hiring_intelligence import team_analytics as team_mod
        from src.ai.agents.hiring_intelligence import trend_analysis as trend_mod
        from src.ai.agents.hiring_intelligence import validators

        provider = self.data_provider
        data_available = bool(getattr(provider, "is_available", lambda: False)())

        cohort = build_cohort_snapshots(candidates, jd, self.insights_fn)
        distributions = build_distributions(cohort)

        kpis = kpi_mod.build_kpis(cohort, provider, data_available)
        bottlenecks = pipeline_mod.build_bottlenecks(cohort, provider, data_available)
        team_metrics = team_mod.build_team_metrics(cohort, provider, data_available)
        trends = trend_mod.build_trends(cohort, provider, data_available)
        capacity = capacity_mod.build_capacity(cohort, provider, data_available)
        forecast = forecast_mod.build_forecast(cohort, data_available)
        benchmarks = benchmark_mod.build_benchmarks(cohort, data_available)
        optimizations = optimization_mod.build_optimizations(cohort, kpis, data_available)

        evidence = {
            "cohort_size": len(cohort),
            "data_available": data_available,
            "distributions": [d.to_dict() for d in distributions],
            "kpis": [k.to_dict() for k in kpis],
            "bottlenecks": [b.to_dict() for b in bottlenecks],
            "team_metrics": [t.to_dict() for t in team_metrics],
            "trends": [t.to_dict() for t in trends],
            "capacity": [c.to_dict() for c in capacity],
            "forecast": [f.to_dict() for f in forecast],
            "benchmarks": [b.to_dict() for b in benchmarks],
            "optimizations": [o.to_dict() for o in optimizations],
            "key_insights": insights_mod.build_key_insights(cohort, kpis, bottlenecks, optimizations, data_available),
        }

        narrative = self._narrative(evidence)

        chart_data = charts_mod.build_chart_data(
            distributions=distributions, kpis=kpis, bottlenecks=bottlenecks,
            team_metrics=team_metrics, forecast=forecast, optimizations=optimizations,
        )

        warnings = validators.evidence_coverage_warnings(evidence)
        warnings += validators.validate_safety(narrative, kpis, trends, data_available)

        return HiringIntelligenceReport(
            report_id=self._next_report_id(),
            generated_on=generated_on,
            cohort_size=len(cohort),
            data_available=data_available,
            distributions=distributions,
            kpis=kpis,
            bottlenecks=bottlenecks,
            team_metrics=team_metrics,
            trends=trends,
            capacity=capacity,
            forecast=forecast,
            benchmarks=benchmarks,
            optimizations=optimizations,
            narrative=narrative,
            charts=chart_data,
            evidence_sources=self._sources(cohort, data_available),
            warnings=list(dict.fromkeys(warnings)),
        )

    # -- narrative ----------------------------------------------------------

    def _narrative(self, evidence: Dict[str, Any]) -> WorkforceNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        payload = HiringIntelligenceInput(
            cohort_size=evidence["cohort_size"],
            data_available=evidence["data_available"],
            analytics=evidence,
        )
        try:
            result = self.ai_runner.run(hiring_intelligence_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return WorkforceNarrative(**compose_workforce_narrative(build_intelligence_evidence(payload)))

    @staticmethod
    def _sources(cohort: List[Dict[str, Any]], data_available: bool) -> List[str]:
        sources = ["Candidate Intelligence engine", "Resume Risk Detection", "Hiring Recommendation engine"]
        if data_available:
            sources.append("Connected workforce-analytics data")
        return sources

    @classmethod
    def _next_report_id(cls) -> str:
        """Return a process-unique report id."""
        cls._counter += 1
        return f"workforce_intel_{cls._counter}"


# A shared default engine for the tool / copilot / UI.
hiring_intelligence_engine = HiringIntelligenceEngine()
