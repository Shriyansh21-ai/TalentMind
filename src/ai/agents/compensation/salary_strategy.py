"""Compensation recommendation + offer strategy (Modules 1, 5).

Wraps the :mod:`pay_band` heuristic model into the recommended range (Module 1)
and derives the four offer scenarios — Conservative / Competitive / Premium /
Aggressive — each positioned within (or stretching beyond) the recommended band,
with advantages, risks, negotiation / retention / business impact (Module 5).
Deterministic and offline; every figure is a heuristic estimate, never fabricated
market data (Module 16).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compensation.pay_band import derive_pay_band
from src.ai.agents.compensation.schemas import CompensationRange, OfferScenario
from src.ai.agents.compensation.templates import SCENARIO_SPECS


def build_recommended_range(evidence: dict[str, Any]) -> CompensationRange:
    """Return the recommended compensation range (Module 1)."""
    return derive_pay_band(evidence)


def _point(band: CompensationRange, anchor: float, stretch: float) -> float:
    """Return the salary point at ``anchor`` (0..1) across the band, plus stretch."""
    value = band.minimum + (band.maximum - band.minimum) * anchor
    if stretch:
        value *= 1.0 + stretch
    return round(value, 2)


def _scenario_range(band: CompensationRange, anchor: float, stretch: float) -> CompensationRange:
    """Build a narrow scenario range centred on the anchor point."""
    target = _point(band, anchor, stretch)
    half = (band.maximum - band.minimum) * 0.10
    return CompensationRange(
        currency=band.currency,
        unit=band.unit,
        minimum=round(max(band.minimum, target - half), 2),
        target=target,
        maximum=round(target + half, 2),
        confidence=band.confidence,
        confidence_label=band.confidence_label,
        basis=[f"Positioned within the recommended band ({band.formatted()})."],
        assumptions=list(band.assumptions),
    )


# Per-scenario qualitative framing (Module 5).
_SCENARIO_FRAMING = {
    "conservative": {
        "advantages": ["Protects the budget", "Leaves room to negotiate up"],
        "risks": ["May read as low intent", "Risk of losing a contested candidate"],
        "negotiation_impact": "Expect a counter; hold headroom to the target.",
        "retention_impact": "Adequate if non-comp factors are strong; watch early attrition.",
        "business_impact": "Lowest cash outlay; best when the pipeline has alternatives.",
    },
    "competitive": {
        "advantages": ["Market-competitive signal", "Balances cost and close rate"],
        "risks": ["Limited headroom on a strong counter"],
        "negotiation_impact": "A fair anchor; small movement usually closes.",
        "retention_impact": "Solid; aligns pay with assessed value.",
        "business_impact": "Balanced investment for a standard growth hire.",
    },
    "premium": {
        "advantages": ["Signals strong intent", "High close probability"],
        "risks": ["Above-target cost", "May raise internal-equity questions"],
        "negotiation_impact": "Minimal negotiation expected.",
        "retention_impact": "Strong; reduces early poaching risk.",
        "business_impact": "Justified for high-impact or scarce-skill hires.",
    },
    "aggressive": {
        "advantages": ["Wins a contested candidate fast", "Removes comp as an objection"],
        "risks": ["Highest cost", "Compression / equity risk with peers", "Sets a precedent"],
        "negotiation_impact": "Pre-empts negotiation entirely.",
        "retention_impact": "Very strong short-term; must be defensible long-term.",
        "business_impact": "Reserve for critical or strategic hires with executive sponsorship.",
    },
}


def build_scenarios(evidence: dict[str, Any], band: CompensationRange) -> list[OfferScenario]:
    """Build the four offer scenarios positioned within the recommended band (Module 5)."""
    scenarios: list[OfferScenario] = []
    for spec in SCENARIO_SPECS:
        framing = _SCENARIO_FRAMING.get(spec.key, {})
        scenarios.append(
            OfferScenario(
                name=spec.name,
                comp_range=_scenario_range(band, spec.anchor, spec.stretch),
                advantages=list(framing.get("advantages", [])),
                risks=list(framing.get("risks", [])),
                negotiation_impact=framing.get("negotiation_impact", ""),
                retention_impact=framing.get("retention_impact", ""),
                business_impact=framing.get("business_impact", ""),
            )
        )
    return scenarios
