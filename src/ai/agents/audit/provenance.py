"""Evidence provenance (Module 2).

For every catalog agent, records where its evidence came from: source, type,
origin agent, a qualitative confidence, and the modules it supports. Provenance is
**derived from the observed evidence sources** — a participating agent is recorded
Observed; an absent one is recorded with register Unavailable and confidence
"Unknown". Nothing is fabricated (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.audit.schemas import ProvenanceRecord
from src.ai.agents.audit.templates import AGENT_CATALOG


def _confidence_for(source: str, context: Dict[str, Any]) -> str:
    """Return a qualitative confidence for a source from the observed signals."""
    # Reuse the governance-risk / equity signals already computed where they map;
    # otherwise report the confidence as a qualitative "Recorded" (present) marker.
    if source == "Pay Equity Guardian":
        level = context.get("equity_risk_level", "")
        return f"Equity risk {level}" if level and level != "Unknown" else "Recorded"
    if source == "Hiring Compliance":
        gr = (context.get("governance_risk") or {}).get("level")
        return f"Governance risk {gr}" if gr else "Recorded"
    return "Recorded"


def build_provenance(context: Dict[str, Any]) -> List[ProvenanceRecord]:
    """Build the evidence provenance records (Module 2)."""
    sources = set(context.get("evidence_sources", []))
    records: List[ProvenanceRecord] = []
    for entry in AGENT_CATALOG:
        present = entry.source in sources
        records.append(
            ProvenanceRecord(
                evidence_source=entry.source,
                evidence_type=entry.evidence_type,
                origin_agent=entry.origin_agent,
                confidence=_confidence_for(entry.source, context) if present else "Unknown",
                supporting_modules=list(entry.feeds),
                register="Observed" if present else "Unavailable",
            )
        )
    return records
