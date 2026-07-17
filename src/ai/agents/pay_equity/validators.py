"""Safety + coverage validators for the Pay Equity Guardian (Module 14).

Pure functions that (a) report which evidence sources were available and (b)
assert the safety guarantees: when internal data is unavailable the compression /
inversion assessments MUST say so (not assume a benign result), the narrative must
contain no legal-conclusion or discrimination language, and the equity risk must be
"Unknown" without data. No I/O.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.pay_equity.schemas import (
    CompressionAssessment,
    EquityRisk,
    InversionAssessment,
    PayEquityNarrative,
)

_SOURCE_LABELS = {
    "compensation": "Compensation Governance Agent",
    "intelligence": "Candidate Intelligence engine",
    "timeline": "Career Timeline Intelligence",
    "risk": "Resume Risk Detection",
    "recommendation": "Hiring Recommendation engine",
    "committee": "AI Hiring Committee",
    "internal_data": "Connected internal compensation data",
}

# Accusatory language that would indicate an unsupported legal / discrimination
# CONCLUSION. These are phrased as accusations so a negating disclaimer (e.g.
# "makes no discrimination finding") does not trip the guard.
_FORBIDDEN_PHRASES = (
    "is discriminatory",
    "discriminates against",
    "constitutes discrimination",
    "discrimination against",
    "unlawful discrimination",
    "illegal",
    "violates the law",
    "breaks the law",
    "lawsuit",
    "legally liable",
    "guilty of",
)


def available_sources(evidence: dict[str, Any]) -> list[str]:
    """Return the labels of the evidence sources actually present + non-empty."""
    sources: list[str] = []
    for key, label in _SOURCE_LABELS.items():
        if evidence.get(key):
            sources.append(label)
    return list(dict.fromkeys(sources))


def evidence_coverage_warnings(evidence: dict[str, Any]) -> list[str]:
    """Return warnings when key evidence sources are missing (Module 14)."""
    warnings: list[str] = []
    if not evidence.get("data_available"):
        warnings.append(
            "No internal compensation data connected — compression, inversion and "
            "band-consistency checks could not run. Findings are provisional."
        )
    if not evidence.get("compensation"):
        warnings.append("No compensation-governance offer available — equity review is limited.")
    return warnings


def validate_safety(
    narrative: PayEquityNarrative,
    compression: CompressionAssessment,
    inversion: InversionAssessment,
    equity_risk: EquityRisk,
    data_available: bool,
) -> list[str]:
    """Assert the no-fabrication / no-legal-conclusion guarantees (Module 14)."""
    warnings: list[str] = []

    if not data_available:
        if compression.data_available or compression.risk_level != "Unavailable":
            warnings.append("Compression reported a result without internal data; flagged.")
        if inversion.data_available or inversion.risk_level != "Unavailable":
            warnings.append("Inversion reported a result without internal data; flagged.")
        if equity_risk.level != "Unknown":
            warnings.append("Equity risk scored without internal data; must be 'Unknown'.")

    # No legal / discrimination conclusions anywhere in the narrative.
    blob = " ".join(str(v) for v in narrative.to_dict().values() if isinstance(v, str)).lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in blob:
            warnings.append(
                f"Narrative contains unsupported legal/discrimination language ({phrase!r}); flagged."
            )

    return warnings
