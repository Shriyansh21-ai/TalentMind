"""Compensation governance policy configuration (Modules 3, 5, 14).

Pure configuration (no engine / UI import) shared by the strategy, governance,
budget and equity modules:

* :data:`PREMIUM_FACTORS` — the heuristic multipliers the internal model applies
  for skill / leadership / strategic premiums and risk discounts (Module 3).
  These are **internal heuristics**, never market survey figures (Module 16).
* :data:`SCENARIO_SPECS` — the four offer scenarios and where each sits in the
  recommended band (Module 5).
* :data:`HRIS_CONNECTORS` — the *names* of the future HRIS / payroll systems the
  equity interface is designed to plug into (Module 14). No connector is
  implemented — this is an extension-point registry only.
* :data:`APPROVAL_POLICY` — which approvers a scenario/hire-type requires
  (Module 12 audit trail).

Adding a scenario, premium or future connector is a one-entry data change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# Heuristic band multipliers (internal model — NOT market data). Applied to the
# candidate's own stated expectation to build a defensible range.
PREMIUM_FACTORS = {
    "skill_premium": 0.08,  # strong technical signal
    "leadership_premium": 0.10,  # strong leadership signal
    "strategic_premium": 0.12,  # committee "Strong Hire" / critical role
    "risk_discount": 0.10,  # elevated resume/timeline risk
    "band_spread": 0.15,  # half-width of the min..max band around target
}

# Thresholds (0-100 engine scales) that trigger each premium/discount.
PREMIUM_THRESHOLDS = {
    "technical_strong": 75.0,
    "leadership_strong": 70.0,
    "confidence_high": 75.0,
}


@dataclass(frozen=True)
class ScenarioSpec:
    """Where a named offer scenario sits within the recommended band (Module 5).

    ``anchor`` is a 0..1 position across [minimum, maximum]; ``stretch`` lets the
    Aggressive scenario extend slightly beyond the maximum.
    """

    key: str
    name: str
    anchor: float
    stretch: float = 0.0
    summary: str = ""


SCENARIO_SPECS: list[ScenarioSpec] = [
    ScenarioSpec(
        "conservative",
        "Conservative Offer",
        anchor=0.15,
        summary="Protects budget; anchors near the band minimum.",
    ),
    ScenarioSpec(
        "competitive",
        "Competitive Offer",
        anchor=0.5,
        summary="Market-competitive; anchors at the target.",
    ),
    ScenarioSpec(
        "premium",
        "Premium Offer",
        anchor=0.85,
        summary="Signals strong intent; anchors near the band maximum.",
    ),
    ScenarioSpec(
        "aggressive",
        "Aggressive Offer",
        anchor=1.0,
        stretch=0.08,
        summary="Wins a contested candidate; stretches beyond the band.",
    ),
]


# Module 14 — extension-point registry. These are the systems the internal-equity
# interface is DESIGNED for; none is implemented (no payroll connectors ship).
HRIS_CONNECTORS: list[str] = [
    "Generic HRIS",
    "SAP SuccessFactors",
    "Workday",
    "Oracle HCM",
    "ADP",
    "Regional Compensation Database",
]

# Additional prepared (not implemented) extension points (Module 14).
FUTURE_CAPABILITIES: list[str] = [
    "Currency conversion",
    "Benefits optimization",
    "Equity valuation",
]


# Module 12 — which approvers a decision requires, by hire type + scenario.
APPROVAL_POLICY = {
    "base": ["Finance", "HR"],
    "critical_hire": ["Finance", "HR", "Executive Sponsor"],
    "aggressive_offer": ["Finance", "HR", "Executive Sponsor"],
    "equity_review": ["HR (Compensation)"],
}
