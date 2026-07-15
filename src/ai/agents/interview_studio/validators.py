"""Provenance + safety validators for the Interview Studio (Module 16).

Every element of the interview package must (a) trace back to an existing
intelligence source and (b) keep Evidence, Inference and Recommendation
separate. These helpers build the provenance ledger, flag any statement that
lacks a source, and report which evidence sources were actually available. They
are pure functions over the assembled artefacts — no I/O.
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.interview_studio.schemas import (
    InterviewStudioNarrative,
    ProvenanceEntry,
    RiskValidation,
)

ALLOWED_KINDS = ("Evidence", "Inference", "Recommendation")

# Human labels for each evidence source key present in the evidence dict.
_SOURCE_LABELS = {
    "resume": "Resume Analyst Agent",
    "jd": "JD Analyst Agent",
    "committee": "AI Hiring Committee",
    "intelligence": "Candidate Intelligence engine",
    "timeline": "Career Timeline Intelligence",
    "risk": "Resume Risk Detection",
    "recommendation": "Hiring Recommendation engine",
    "interview": "Interview Intelligence",
}


def available_sources(evidence: Dict[str, Any]) -> List[str]:
    """Return the labels of the evidence sources actually present + non-empty."""
    sources: List[str] = []
    for key, label in _SOURCE_LABELS.items():
        value = evidence.get(key)
        if value:  # non-empty dict / list
            sources.append(label)
    return list(dict.fromkeys(sources))


def build_provenance(
    narrative: InterviewStudioNarrative,
    evidence: Dict[str, Any],
    risk_validations: List[RiskValidation],
) -> List[ProvenanceEntry]:
    """Build the evidence->claim ledger for the interview package.

    Separates the three registers (Module 16):
    * Evidence — the upstream sources that fed the plan.
    * Inference — the studio's interpretation (personalization, readiness).
    * Recommendation — the forward-looking interview focus.
    """
    entries: List[ProvenanceEntry] = []

    # Evidence: every available upstream source.
    for label in available_sources(evidence):
        entries.append(
            ProvenanceEntry(kind="Evidence", statement=f"Consumed structured output from {label}.", source=label)
        )

    # Evidence: each risk validation traces to a concrete source.
    for rv in risk_validations[:6]:
        entries.append(
            ProvenanceEntry(
                kind="Evidence",
                statement=f"Risk '{rv.risk}' converted into a validation question.",
                source=rv.source,
            )
        )

    # Inference: the studio's interpretive framing.
    if narrative.personalization_note:
        entries.append(
            ProvenanceEntry(kind="Inference", statement=narrative.personalization_note, source="Interview Studio")
        )
    if narrative.readiness_label:
        entries.append(
            ProvenanceEntry(
                kind="Inference",
                statement=f"Interview readiness assessed as '{narrative.readiness_label}'.",
                source="Interview Studio",
            )
        )

    # Recommendation: the forward-looking interview focus.
    if narrative.recommended_focus:
        entries.append(
            ProvenanceEntry(kind="Recommendation", statement=narrative.recommended_focus, source="Interview Studio")
        )

    return entries


def validate_provenance(provenance: List[ProvenanceEntry]) -> List[str]:
    """Return warnings for any provenance entry missing a source or kind."""
    warnings: List[str] = []
    for entry in provenance:
        if not entry.source:
            warnings.append(f"Provenance statement without a source: {entry.statement!r}.")
        if entry.kind not in ALLOWED_KINDS:
            warnings.append(f"Provenance entry has an unknown kind {entry.kind!r}.")
    return warnings


def evidence_coverage_warnings(evidence: Dict[str, Any]) -> List[str]:
    """Return warnings when key evidence sources are missing (Module 16)."""
    warnings: List[str] = []
    if not (evidence.get("jd")):
        warnings.append("No JD analysis available — role-fit personalization is limited.")
    if not (evidence.get("committee")):
        warnings.append("No committee decision available — decision-matrix alignment is weaker.")
    if len(available_sources(evidence)) < 4:
        warnings.append("Fewer than 4 evidence sources; treat the plan as provisional.")
    return warnings
