"""Optimization engine (Module 9).

Generates prioritized improvement opportunities from the catalog, activating each
only when the cohort/KPI conditions that justify it are observed. Priority is
computed from impact vs. implementation effort (Module 9). Every item is a
**Recommendation** — it surfaces improvements, it does not fabricate results.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.hiring_intelligence.analytics_engine import is_positive, share
from src.ai.agents.hiring_intelligence.schemas import KPI, Optimization
from src.ai.agents.hiring_intelligence.templates import OPTIMIZATION_CATALOG

# impact x effort -> priority.
_PRIORITY = {
    ("High", "Low"): "Critical",
    ("High", "Medium"): "High",
    ("High", "High"): "Medium",
    ("Medium", "Low"): "High",
    ("Medium", "Medium"): "Medium",
    ("Medium", "High"): "Low",
    ("Low", "Low"): "Medium",
    ("Low", "Medium"): "Low",
    ("Low", "High"): "Low",
}


def _fires(
    trigger: str, cohort: list[dict[str, Any]], kpis: list[KPI], data_available: bool
) -> bool:
    """Return whether an optimization's trigger condition holds."""
    if trigger == "no_provider":
        return not data_available
    if trigger == "high_risk_share":
        return share(cohort, lambda s: s["risk_level"] == "High") >= 0.3
    if trigger == "low_interview_ready":
        return share(cohort, lambda s: not s.get("interview_ready")) >= 0.5
    if trigger == "weak_recommendation_share":
        return share(cohort, lambda s: not is_positive(s["recommendation"])) >= 0.5
    if trigger in ("governance_unavailable", "audit_unavailable"):
        # These KPIs are Unavailable without a governance/analytics source.
        target = "Governance Health" if trigger == "governance_unavailable" else "Audit Readiness"
        return any(k.name == target and k.register == "Unavailable" for k in kpis)
    return False


def build_optimizations(
    cohort: list[dict[str, Any]], kpis: list[KPI], data_available: bool
) -> list[Optimization]:
    """Generate prioritized optimization opportunities (Module 9)."""
    optimizations: list[Optimization] = []
    for definition in OPTIMIZATION_CATALOG:
        if not _fires(definition.trigger, cohort, kpis, data_available):
            continue
        optimizations.append(
            Optimization(
                area=definition.area,
                recommendation=definition.recommendation,
                impact=definition.impact,
                effort=definition.effort,
                priority=_PRIORITY.get((definition.impact, definition.effort), "Medium"),
                register="Recommendation",
            )
        )

    if not optimizations:
        optimizations.append(
            Optimization(
                area="Process",
                recommendation="No material optimization opportunities surfaced from the current cohort.",
                impact="Low",
                effort="Low",
                priority="Low",
                register="Recommendation",
            )
        )
    # Highest-priority first.
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    optimizations.sort(key=lambda o: order.get(o.priority, 3))
    return optimizations
