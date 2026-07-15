"""Visualization data for the Workforce Intelligence dashboard (Module 11).

Pure data builders (no plotting, no Streamlit import): hiring health, pipeline
flow (bottlenecks), trend timeline, executive KPIs, capacity, department/role
comparison, governance health and optimization opportunities. Every value is a
count / qualitative status / cohort-derived number — never a fabricated enterprise
statistic.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.hiring_intelligence.schemas import (
    Bottleneck,
    Distribution,
    ForecastScenario,
    KPI,
    Optimization,
    TeamMetric,
)


def build_chart_data(
    *,
    distributions: List[Distribution],
    kpis: List[KPI],
    bottlenecks: List[Bottleneck],
    team_metrics: List[TeamMetric],
    forecast: List[ForecastScenario],
    optimizations: List[Optimization],
) -> Dict[str, Any]:
    """Build every chart structure for the workforce dashboard (Module 11)."""
    return {
        "distributions": {d.name: d.counts for d in distributions},
        "executive_kpis": {
            k.name: {"value": k.value, "label": k.label, "register": k.register} for k in kpis
        },
        "hiring_health": next(
            ({"value": k.value, "label": k.label} for k in kpis if k.name == "Hiring Health Index"),
            {"value": None, "label": "n/a"},
        ),
        "pipeline_flow": [
            {"stage": b.stage, "severity": b.severity, "register": b.register} for b in bottlenecks
        ],
        "department_comparison": [
            {"dimension": t.dimension, "group": t.group, "count": t.count, "hiring_health": t.hiring_health}
            for t in team_metrics if t.register == "Observed"
        ],
        "forecast": {
            f.name: {"growth": f.growth_label, "confidence": f.confidence} for f in forecast
        },
        "optimization_opportunities": [
            {"area": o.area, "priority": o.priority, "impact": o.impact, "effort": o.effort}
            for o in optimizations
        ],
        "governance_health": next(
            ({"value": k.value, "label": k.label, "register": k.register} for k in kpis if k.name == "Governance Health"),
            {"value": None, "label": "Unavailable", "register": "Unavailable"},
        ),
    }
