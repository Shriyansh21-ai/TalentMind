"""Safety + coverage validators for the Hiring Intelligence Agent (Module 15).

Pure functions that (a) report evidence coverage and (b) assert the
no-fabrication guarantees: a KPI/trend that needs connected data must NOT report a
numeric value when unavailable, and the narrative must not present a forecast as a
certain prediction. No I/O.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.hiring_intelligence.schemas import KPI, Trend, WorkforceNarrative

# Language that would over-claim forecast certainty (Module 7 / 15).
_FORBIDDEN_PHRASES = (
    "will definitely",
    "guaranteed to",
    "certain to hire",
    "we predict exactly",
    "with certainty",
)


def available_sources(evidence: dict[str, Any]) -> list[str]:
    """Return the evidence sources actually consulted."""
    sources = [
        "Candidate Intelligence engine",
        "Resume Risk Detection",
        "Hiring Recommendation engine",
    ]
    if evidence.get("data_available"):
        sources.append("Connected workforce-analytics data")
    return sources


def evidence_coverage_warnings(evidence: dict[str, Any]) -> list[str]:
    """Return warnings when analytics data is missing (Module 15)."""
    analytics = evidence.get("analytics") or evidence
    warnings: list[str] = []
    if not analytics.get("data_available"):
        warnings.append(
            "No workforce-analytics source connected — trends, delays, team breakdowns and "
            "capacity are unavailable; the report analyses a bounded cohort only."
        )
    if analytics.get("cohort_size", 0) < 3:
        warnings.append("Analyzed cohort is very small; cohort statistics are directional only.")
    return warnings


def validate_safety(
    narrative: WorkforceNarrative,
    kpis: list[KPI],
    trends: list[Trend],
    data_available: bool,
) -> list[str]:
    """Assert the no-fabrication / no-false-certainty guarantees (Module 15)."""
    warnings: list[str] = []

    # Unavailable KPIs/trends must carry no numeric value / no concrete direction.
    for k in kpis:
        if k.register == "Unavailable" and k.value is not None:
            warnings.append(f"KPI '{k.name}' is Unavailable but carries a value; flagged.")
    for t in trends:
        if t.register == "Unavailable" and t.direction not in ("Unavailable",):
            warnings.append(f"Trend '{t.name}' is Unavailable but claims a direction; flagged.")

    # No false forecast certainty in the narrative.
    blob = " ".join(str(v) for v in narrative.to_dict().values() if isinstance(v, str)).lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in blob:
            warnings.append(f"Narrative over-claims forecast certainty ({phrase!r}); flagged.")

    return warnings
