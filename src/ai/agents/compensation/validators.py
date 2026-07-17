"""Safety + coverage validators for Compensation Governance (Module 16).

Pure functions that (a) report which evidence sources were actually available,
(b) warn when key evidence is missing, and (c) assert the no-fabrication
guarantees: the market position must be honest about the absence of external
data, internal equity must be flagged unavailable when no payroll source is
connected, and the recommended band must carry its internal-heuristic disclaimer.
No I/O.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compensation.schemas import (
    CompensationRange,
    InternalEquityReadiness,
    MarketPosition,
)

# Human labels for each evidence source key present in the evidence dict.
_SOURCE_LABELS = {
    "candidate_comp": "Candidate stated expectation",
    "resume": "Resume Analyst Agent",
    "jd": "JD Analyst Agent",
    "committee": "AI Hiring Committee",
    "intelligence": "Candidate Intelligence engine",
    "timeline": "Career Timeline Intelligence",
    "risk": "Resume Risk Detection",
    "recommendation": "Hiring Recommendation engine",
    "interview": "Interview Intelligence",
}


def available_sources(evidence: dict[str, Any]) -> list[str]:
    """Return the labels of the evidence sources actually present + non-empty."""
    sources: list[str] = []
    for key, label in _SOURCE_LABELS.items():
        if evidence.get(key):
            sources.append(label)
    return list(dict.fromkeys(sources))


def evidence_coverage_warnings(evidence: dict[str, Any]) -> list[str]:
    """Return warnings when key evidence sources are missing (Module 16)."""
    warnings: list[str] = []
    if not (evidence.get("candidate_comp") or {}).get("expected_max"):
        warnings.append(
            "Candidate stated no salary expectation; the band is anchored on a "
            "seniority baseline assumption."
        )
    if not evidence.get("jd"):
        warnings.append("No JD analysis available — role-alignment governance is limited.")
    if not evidence.get("committee"):
        warnings.append("No committee decision available — strategic-premium governance is weaker.")
    if len(available_sources(evidence)) < 4:
        warnings.append("Fewer than 4 evidence sources; treat the recommendation as provisional.")
    return warnings


def validate_no_fabrication(
    band: CompensationRange,
    market: MarketPosition,
    equity: InternalEquityReadiness,
) -> list[str]:
    """Assert the no-fabrication guarantees; return warnings on any violation."""
    warnings: list[str] = []

    # Market position must be honest about the absence of external data.
    if not market.data_available and "internal heuristic" not in (market.data_note or "").lower():
        warnings.append("Market position claims external data without a source; flagged.")

    # Internal equity must be unavailable unless a real provider was injected.
    if not equity.available and equity.status_message != "Internal equity validation unavailable.":
        warnings.append(
            "Internal equity reported as unavailable but the status message is inconsistent."
        )

    # The band must carry its internal-heuristic disclaimer.
    if not any("internal heuristic" in a.lower() for a in band.assumptions):
        warnings.append("Recommended band is missing its internal-heuristic-model disclaimer.")

    # A range must never collapse to a single point (Module 1).
    if band.minimum == band.maximum:
        warnings.append("Recommendation collapsed to a single figure; a range is required.")

    return warnings
