"""Pay-equity policy + integration configuration (Modules 5, 12).

Pure configuration (no engine / UI import) shared across the equity modules:

* :data:`PAY_POLICIES` — the **configurable** company pay philosophies (Pay-Band
  First, Market First, Performance First, Strategic Hire, Critical Talent). These
  are data entries, never hardcoded logic (Module 5); a caller may also inject a
  custom :class:`PayPolicy`.
* :data:`HRIS_PROVIDERS` — the *names* of the future HRIS / payroll systems the
  data-provider interface is designed to plug into (Module 12). No connector is
  implemented — this is an extension-point registry only.
* :data:`APPROVAL_LADDER` — the ordered approver roles the executive-review engine
  escalates through (Module 7).

Adding a policy or a future provider is a one-entry data change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class PayPolicy:
    """A configurable company pay philosophy (Module 5 — data, not code).

    Attributes:
        key: Stable policy key.
        name: Human-readable policy name.
        summary: One-line description of the philosophy.
        priority_factors: Ordered factors the policy optimizes for.
        review_triggers: Conditions (keys the engine understands) that require a
            human review under this policy.
    """

    key: str
    name: str
    summary: str
    priority_factors: list[str] = field(default_factory=list)
    review_triggers: list[str] = field(default_factory=list)


PAY_POLICIES: dict[str, PayPolicy] = {
    "pay_band_first": PayPolicy(
        key="pay_band_first",
        name="Pay-Band First",
        summary="Internal pay-band consistency takes precedence over market or performance.",
        priority_factors=["pay_band_consistency", "internal_equity", "market", "performance"],
        review_triggers=["outside_band", "compression_high", "inversion_detected"],
    ),
    "market_first": PayPolicy(
        key="market_first",
        name="Market First",
        summary="Market competitiveness leads; internal equity is monitored, not gating.",
        priority_factors=["market", "internal_equity", "pay_band_consistency", "performance"],
        review_triggers=["compression_high", "inversion_detected"],
    ),
    "performance_first": PayPolicy(
        key="performance_first",
        name="Performance First",
        summary="Assessed performance/capability leads; equity flagged for review.",
        priority_factors=["performance", "market", "internal_equity", "pay_band_consistency"],
        review_triggers=["compression_high", "inversion_detected"],
    ),
    "strategic_hire": PayPolicy(
        key="strategic_hire",
        name="Strategic Hire",
        summary="Strategic value can justify a premium; equity impact must be documented.",
        priority_factors=["strategic_value", "market", "internal_equity"],
        review_triggers=[
            "compression_medium",
            "compression_high",
            "inversion_detected",
            "outside_band",
        ],
    ),
    "critical_talent": PayPolicy(
        key="critical_talent",
        name="Critical Talent",
        summary="Scarce/critical talent can exceed the band with executive sponsorship.",
        priority_factors=["strategic_value", "market", "internal_equity", "pay_band_consistency"],
        review_triggers=["outside_band", "inversion_detected", "compression_high"],
    ),
}

DEFAULT_POLICY = "pay_band_first"


def get_policy(key: str) -> PayPolicy:
    """Return the pay policy for ``key`` (falls back to the default)."""
    return PAY_POLICIES.get((key or "").strip().lower(), PAY_POLICIES[DEFAULT_POLICY])


def list_policies() -> list[PayPolicy]:
    """Return every registered pay policy (stable order)."""
    return list(PAY_POLICIES.values())


# Module 12 — extension-point registry. The systems the data-provider interface is
# DESIGNED for; none is implemented (no payroll connectors ship).
HRIS_PROVIDERS: list[str] = [
    "Workday",
    "SAP SuccessFactors",
    "Oracle HCM",
    "ADP",
    "BambooHR",
    "UKG",
    "HiBob",
    "Generic Payroll API",
]

# Module 7 — ordered approver ladder for the executive-review engine.
APPROVAL_LADDER: list[str] = [
    "Recruiter",
    "Hiring Manager",
    "HR",
    "Finance",
    "Legal",
    "Executive",
]
