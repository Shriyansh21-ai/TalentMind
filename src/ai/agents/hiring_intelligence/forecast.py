"""Hiring forecast (Module 7).

Produces scenario-based demand forecasts by scaling the analyzed cohort's current
volume — Conservative (+10%), Growth (+25%) and Aggressive (+50%). Every scenario
carries explicit assumptions and a bounded confidence and is tagged **Forecast**;
it **never claims prediction certainty** and never fabricates a historical base
rate (Module 7 / 15).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.hiring_intelligence.schemas import ForecastScenario

# (name, growth label, multiplier, confidence).
_SCENARIOS = [
    ("Conservative", "+10% hiring growth", 1.10, 55.0),
    ("Growth", "+25% hiring growth", 1.25, 45.0),
    ("Aggressive", "+50% hiring growth", 1.50, 30.0),
]

# Downstream demand areas scaled with hiring volume.
_DEMAND_AREAS = [
    "Approval demand",
    "Interview demand",
    "Committee demand",
    "Governance demand",
    "Compliance demand",
]


def _label(current: int, multiplier: float) -> str:
    projected = round(current * multiplier)
    return f"~{projected} (from {current})"


def build_forecast(cohort: list[dict[str, Any]], data_available: bool) -> list[ForecastScenario]:
    """Produce scenario-based hiring-demand forecasts (Module 7)."""
    current = len(cohort)
    base_assumptions = [
        "Baseline is the ANALYZED COHORT volume, not verified org-wide hiring volume.",
        "Downstream demand is assumed to scale linearly with hiring volume.",
        "No historical base rate is connected; treat figures as directional, not predictions.",
    ]

    scenarios: list[ForecastScenario] = []
    for name, growth, mult, conf in _SCENARIOS:
        demand = {area: _label(current, mult) for area in _DEMAND_AREAS}
        scenarios.append(
            ForecastScenario(
                name=name,
                growth_label=growth,
                demand=demand,
                confidence=conf,
                assumptions=list(base_assumptions)
                + (
                    ["A connected analytics source would sharpen these estimates."]
                    if not data_available
                    else []
                ),
                register="Forecast",
            )
        )
    return scenarios
