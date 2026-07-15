"""Key insights synthesis + report scaffolding (Module 10).

Synthesizes the headline strategic insights the executive narrative leads with,
and owns the ordered section registry for the Module 10 executive workforce
report. Pure synthesis over the already-computed analytics — no recomputation, no
fabrication (Module 15).
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.ai.agents.hiring_intelligence.schemas import KPI, Bottleneck, Optimization

# Ordered sections of the executive workforce report (Module 10).
REPORT_SECTIONS: List[Tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("key_insights", "Key Insights"),
    ("enterprise_kpis", "Enterprise KPIs"),
    ("trend_analysis", "Trend Analysis"),
    ("risk_areas", "Risk Areas"),
    ("optimization", "Optimization Opportunities"),
    ("strategic_recommendations", "Strategic Recommendations"),
    ("evidence_sources", "Evidence Sources"),
]


def section_titles() -> List[str]:
    """Return the ordered workforce-report section titles."""
    return [title for _key, title in REPORT_SECTIONS]


def build_key_insights(
    cohort: List[Dict[str, Any]],
    kpis: List[KPI],
    bottlenecks: List[Bottleneck],
    optimizations: List[Optimization],
    data_available: bool,
) -> List[str]:
    """Synthesize the headline strategic insights (Module 10)."""
    insights: List[str] = []

    health = next((k for k in kpis if k.name == "Hiring Health Index"), None)
    if health and health.value is not None:
        insights.append(f"Hiring Health Index is {health.label} ({health.value:.0f}/100) across {len(cohort)} analyzed candidates.")

    observed_bottlenecks = [b for b in bottlenecks if b.register == "Estimated"]
    if observed_bottlenecks:
        insights.append("Estimated bottleneck(s): " + "; ".join(b.stage for b in observed_bottlenecks) + ".")

    top_opt = next((o for o in optimizations if o.priority in ("Critical", "High")), None)
    if top_opt:
        insights.append(f"Top optimization ({top_opt.priority}): {top_opt.recommendation}")

    if not data_available:
        insights.append(
            "Trends, delays, team breakdowns and capacity are UNAVAILABLE — no workforce-analytics "
            "source is connected; connect one to unlock time-series intelligence."
        )

    if not insights:
        insights.append("Insufficient cohort data to surface strategic insights.")
    return insights
