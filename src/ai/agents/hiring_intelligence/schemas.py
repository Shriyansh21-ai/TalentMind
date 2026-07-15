"""Structured schemas for the HiringIntelligenceAgent (Phase 5 / Milestone 5).

The **Enterprise Workforce Hiring Intelligence System** answers organizational
questions: how healthy is our hiring organization, where are the bottlenecks,
which teams hire well, which practices should improve, what trends matter and how
future hiring can improve. It provides **strategic organizational intelligence —
never individual candidate ranking**. It is not BI/reporting/dashboard software:
it reasons over the platform's existing intelligence and never fabricates
analytics, trends, KPIs or forecasts (Module 15).

Two families live here:

* :class:`WorkforceNarrative` — the single validated :class:`BaseAIResponse` the
  AI Platform agent produces. **Score-free at the top level** (all numbers live in
  the nested dataclasses).
* Dataclasses (:class:`Distribution`, :class:`KPI`, :class:`Bottleneck`,
  :class:`TeamMetric`, :class:`Trend`, :class:`CapacityEstimate`,
  :class:`ForecastScenario`, :class:`Benchmark`, :class:`Optimization`,
  :class:`HiringIntelligenceReport`) — the assembled analytics artefact.

Every element carries an epistemic register: Observed, Unavailable, Estimated,
Forecast, Recommendation or Human Review (Module 15).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

REGISTERS = ("Observed", "Unavailable", "Estimated", "Forecast", "Recommendation", "Human Review")


# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class WorkforceNarrative(BaseAIResponse):
    """The executive workforce-intelligence narrative the agent produces (Modules 1, 10).

    Score-free at the top level; every figure lives in the nested dataclasses. It
    provides strategic organizational intelligence — never individual ranking — and
    fabricates no enterprise statistics (Module 15).
    """

    executive_summary: str
    health_note: str = ""
    pipeline_note: str = ""
    trend_note: str = ""
    kpi_note: str = ""
    capacity_note: str = ""
    forecast_note: str = ""
    optimization_note: str = ""
    data_availability_note: str = ""
    key_insights: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    strategic_recommendations: List[str] = Field(default_factory=list)
    confidence_note: str = ""

    @field_validator("executive_summary")
    @classmethod
    def _summary_non_empty(cls, value: str) -> str:
        """Ensure the executive summary is a non-empty string."""
        text = (value or "").strip()
        if not text:
            raise ValueError("executive_summary must not be empty")
        return text


# ---------------------------------------------------------------------------
# Module 1 — Distributions (observed cohort aggregates)
# ---------------------------------------------------------------------------


@dataclass
class Distribution:
    """A counted distribution over the analyzed cohort (Module 1)."""

    name: str
    counts: Dict[str, int] = field(default_factory=dict)
    total: int = 0
    register: str = "Observed"
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 5 — Executive KPIs
# ---------------------------------------------------------------------------


@dataclass
class KPI:
    """An evidence-backed executive KPI (Module 5). Value is None when Unavailable."""

    name: str
    value: Optional[float] = None
    label: str = "n/a"  # qualitative band (High/Medium/Low) or "Unavailable"
    register: str = "Observed"
    confidence: float = 0.0
    basis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 1) if isinstance(self.value, (int, float)) else None,
            "label": self.label,
            "register": self.register,
            "confidence": round(self.confidence, 1),
            "basis": self.basis,
        }


# ---------------------------------------------------------------------------
# Module 2 — Pipeline bottlenecks
# ---------------------------------------------------------------------------


@dataclass
class Bottleneck:
    """A pipeline bottleneck (Module 2). Observed timing needs a data provider."""

    stage: str
    severity: str = "Unknown"  # Low | Medium | High | Unknown
    observed: bool = False
    potential_cause: str = ""
    business_impact: str = ""
    improvement: str = ""
    register: str = "Unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 3 — Team analytics
# ---------------------------------------------------------------------------


@dataclass
class TeamMetric:
    """Aggregated hiring health for one team dimension/group (Module 3)."""

    dimension: str
    group: str
    count: int = 0
    hiring_health: str = "n/a"
    register: str = "Observed"
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 4 — Trends
# ---------------------------------------------------------------------------


@dataclass
class Trend:
    """A hiring trend (Module 4). Time-series needs historical event data."""

    name: str
    direction: str = "Unavailable"  # Up | Down | Flat | Unavailable
    evidence: str = ""
    confidence: float = 0.0
    interpretation: str = ""
    register: str = "Unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 6 — Capacity
# ---------------------------------------------------------------------------


@dataclass
class CapacityEstimate:
    """A hiring-capacity estimate (Module 6). Workloads need req/headcount data."""

    area: str
    workload_level: str = "Unavailable"  # Low | Moderate | High | Unavailable
    risk: str = ""
    recommendation: str = ""
    register: str = "Unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 7 — Forecast
# ---------------------------------------------------------------------------


@dataclass
class ForecastScenario:
    """A scenario-based hiring-demand forecast (Module 7). Never certain."""

    name: str
    growth_label: str = ""
    demand: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    assumptions: List[str] = field(default_factory=list)
    register: str = "Forecast"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 8 — Benchmark
# ---------------------------------------------------------------------------


@dataclass
class Benchmark:
    """An internal benchmark comparison (Module 8). Internal data only."""

    dimension: str
    comparisons: List[Dict[str, Any]] = field(default_factory=list)
    register: str = "Observed"
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 9 — Optimization
# ---------------------------------------------------------------------------


@dataclass
class Optimization:
    """A prioritized improvement opportunity (Module 9)."""

    area: str
    recommendation: str
    impact: str = "Medium"  # High | Medium | Low
    effort: str = "Medium"  # High | Medium | Low
    priority: str = "Medium"  # computed from impact vs effort
    register: str = "Recommendation"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Assembled report artefact (Module 10)
# ---------------------------------------------------------------------------


@dataclass
class HiringIntelligenceReport:
    """The unified enterprise workforce-intelligence report (Modules 1-11).

    Aggregates the cohort distributions, KPIs, pipeline bottlenecks, team analytics,
    trends, capacity, forecast, benchmarks and optimizations — every one derived
    from existing intelligence or the (optional) injected analytics provider. It
    provides strategic organizational intelligence only (never candidate ranking)
    and fabricates no enterprise statistics (Modules 14 / 15).
    """

    report_id: str
    generated_on: str
    cohort_size: int
    data_available: bool
    distributions: List[Distribution]
    kpis: List[KPI]
    bottlenecks: List[Bottleneck]
    team_metrics: List[TeamMetric]
    trends: List[Trend]
    capacity: List[CapacityEstimate]
    forecast: List[ForecastScenario]
    benchmarks: List[Benchmark]
    optimizations: List[Optimization]
    narrative: WorkforceNarrative
    charts: Dict[str, Any] = field(default_factory=dict)
    evidence_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "report_id": self.report_id,
            "generated_on": self.generated_on,
            "cohort_size": self.cohort_size,
            "data_available": self.data_available,
            "distributions": [d.to_dict() for d in self.distributions],
            "kpis": [k.to_dict() for k in self.kpis],
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "team_metrics": [t.to_dict() for t in self.team_metrics],
            "trends": [t.to_dict() for t in self.trends],
            "capacity": [c.to_dict() for c in self.capacity],
            "forecast": [f.to_dict() for f in self.forecast],
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "optimizations": [o.to_dict() for o in self.optimizations],
            "narrative": self.narrative.to_dict(),
            "charts": self.charts,
            "evidence_sources": list(self.evidence_sources),
            "warnings": list(self.warnings),
        }
