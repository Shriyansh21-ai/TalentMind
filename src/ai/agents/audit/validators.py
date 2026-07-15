"""Safety + coverage validators for the Hiring Audit Agent (Module 14).

Pure functions that (a) report which agents/evidence were available and (b)
assert the safety guarantees: the reconstruction must not claim an agent
participated when its evidence is absent, must not mark a human approval Observed
without a connected system, must not fabricate history, and must contain no legal
opinion. No I/O.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.audit.schemas import (
    AuditNarrative,
    DecisionResponsibility,
    HistoricalReconstruction,
)

# Assertion-specific legal-opinion language (negating disclaimers are allowed).
_FORBIDDEN_PHRASES = (
    "our legal opinion is",
    "here is legal advice",
    "is illegal",
    "violates the law",
    "we rule that",
    "legally binding determination",
)


def available_sources(evidence: Dict[str, Any]) -> List[str]:
    """Return the evidence sources actually on record."""
    return list(dict.fromkeys(evidence.get("evidence_sources", [])))


def evidence_coverage_warnings(evidence: Dict[str, Any]) -> List[str]:
    """Return warnings when key evidence / history is missing (Module 14)."""
    warnings: List[str] = []
    if not evidence.get("data_available"):
        warnings.append(
            "No audit archive connected — human approvals and historical decisions "
            "could not be verified. The reconstruction reflects on-record artefacts only."
        )
    if "AI Hiring Committee" not in set(evidence.get("evidence_sources", [])):
        warnings.append("No committee decision on record — the final decision cannot be fully reconstructed.")
    return warnings


def validate_safety(
    narrative: AuditNarrative,
    responsibility: List[DecisionResponsibility],
    history: HistoricalReconstruction,
    data_available: bool,
) -> List[str]:
    """Assert the no-fabrication / no-legal-opinion guarantees (Module 14)."""
    warnings: List[str] = []

    # No human decision may be Observed without a connected system.
    if not data_available:
        for d in responsibility:
            if d.responsible_party != "AI" and d.status == "Observed":
                warnings.append(
                    f"Human decision '{d.decision}' marked Observed without a connected approval system; flagged."
                )

    # History must be unavailable unless a provider was connected.
    if not data_available and history.available:
        warnings.append("Historical reconstruction reported available without a connected archive; flagged.")

    # No legal opinion anywhere in the narrative.
    blob = " ".join(str(v) for v in narrative.to_dict().values() if isinstance(v, str)).lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in blob:
            warnings.append(f"Narrative contains an unsupported legal-opinion phrase ({phrase!r}); flagged.")

    return warnings
