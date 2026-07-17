"""Report safety validators (Module 16).

Two guarantees this module enforces for the assembled executive report:

1. **Provenance** — every headline statement is linked to the source engine/agent
   that produced its underlying evidence, so nothing in the report is
   unattributed. :func:`build_provenance` derives that link table from the
   evidence that was actually present.
2. **Register separation** — Evidence, Inference and Recommendation are kept
   distinct and never blurred. :func:`validate_provenance` checks that only the
   three allowed kinds appear and that every entry cites a source.

These are pure functions over dicts/dataclasses — no engine or UI import — so the
builder and the tests can both use them.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.executive_report.schemas import ExecutiveNarrative, ProvenanceEntry

ALLOWED_KINDS = ("Evidence", "Inference", "Recommendation")

# Which engine/agent label backs each evidence key when it is present.
_SOURCE_LABELS = {
    "committee": "AI Hiring Committee",
    "resume": "Resume Analyst Agent",
    "jd": "JD Analyst Agent",
    "intelligence": "Candidate Intelligence engine",
    "timeline": "Career Timeline Intelligence",
    "risk": "Resume Risk Detection",
    "recommendation": "Hiring Recommendation engine",
    "interview": "Interview Intelligence",
    "pipeline": "Hiring Pipeline",
}


def available_sources(evidence: dict[str, Any]) -> list[str]:
    """Return the labels of the evidence sources actually present (ordered)."""
    labels: list[str] = []
    for key, label in _SOURCE_LABELS.items():
        value = evidence.get(key)
        if value:
            labels.append(label)
    return labels


def build_provenance(
    narrative: ExecutiveNarrative, evidence: dict[str, Any]
) -> list[ProvenanceEntry]:
    """Build the provenance table linking narrative claims to their sources.

    Only claims whose backing source is present in the evidence are recorded, so
    the report never attributes a statement to a source it did not consume.
    """
    entries: list[ProvenanceEntry] = []

    def _src(*keys: str) -> str:
        for key in keys:
            if evidence.get(key):
                return _SOURCE_LABELS[key]
        return "TalentMind synthesis"

    # Recommendation register.
    entries.append(
        ProvenanceEntry(
            kind="Recommendation",
            statement=f"Overall recommendation: {narrative.overall_recommendation}",
            source=_src("committee", "recommendation", "intelligence"),
        )
    )

    # Evidence register — facts an engine produced.
    if narrative.business_impact:
        entries.append(
            ProvenanceEntry(
                "Evidence",
                narrative.business_impact,
                _src("committee", "recommendation", "intelligence"),
            )
        )
    if narrative.technical_impact:
        entries.append(
            ProvenanceEntry(
                "Evidence", narrative.technical_impact, _src("committee", "intelligence", "resume")
            )
        )
    if narrative.risk_overview:
        entries.append(
            ProvenanceEntry("Evidence", narrative.risk_overview, _src("risk", "committee"))
        )

    # Inference register — interpretations.
    if narrative.leadership_potential:
        entries.append(
            ProvenanceEntry(
                "Inference", narrative.leadership_potential, _src("intelligence", "timeline")
            )
        )
    if narrative.interview_readiness:
        entries.append(
            ProvenanceEntry(
                "Inference", narrative.interview_readiness, _src("interview", "recommendation")
            )
        )

    return entries


def validate_provenance(entries: list[ProvenanceEntry]) -> list[str]:
    """Return a list of warnings for any provenance rule violation (empty == ok)."""
    warnings: list[str] = []
    for entry in entries:
        if entry.kind not in ALLOWED_KINDS:
            warnings.append(f"Provenance entry has invalid register '{entry.kind}'.")
        if not (entry.source or "").strip():
            warnings.append(f"Statement is unattributed: {entry.statement[:60]!r}.")
        if not (entry.statement or "").strip():
            warnings.append("Provenance entry has an empty statement.")
    return warnings


def evidence_coverage_warnings(evidence: dict[str, Any]) -> list[str]:
    """Return warnings when the report rests on thin evidence (Module 16)."""
    sources = available_sources(evidence)
    warnings: list[str] = []
    if not evidence.get("committee"):
        warnings.append("No committee decision — the executive recommendation is less robust.")
    if not evidence.get("jd"):
        warnings.append("No JD analysis — role-fit framing is limited.")
    if len(sources) < 4:
        warnings.append(f"Only {len(sources)} evidence source(s) available; confidence is reduced.")
    return warnings
