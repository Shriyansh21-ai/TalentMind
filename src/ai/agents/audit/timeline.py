"""Hiring timeline reconstruction (Module 4).

Builds an ordered timeline of the hiring journey — resume, JD, ranking, committee,
interview, compensation, pay-equity, compliance, executive approval, final
decision — marking each Observed or Unavailable and attributing it to an AI /
Human / System actor. Order is by decision-journey sequence (no fabricated
timestamps — Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.audit.schemas import TimelineEvent

# (name, evidence_source that confirms it, actor). Ordered.
_TIMELINE = [
    ("Resume uploaded / analyzed", "Resume Analyst Agent", "System"),
    ("Job description analyzed", "JD Analyst Agent", "System"),
    ("Candidate ranked / assessed", "Candidate Intelligence engine", "AI"),
    ("Risk analysis", "Risk Intelligence", "AI"),
    ("Interview plan generated", "Interview Intelligence", "AI"),
    ("Committee discussion & decision", "AI Hiring Committee", "AI"),
    ("Compensation reviewed", "Compensation Governance Agent", "AI"),
    ("Pay-equity reviewed", "Pay Equity Guardian", "AI"),
    ("Compliance reviewed", "Hiring Compliance", "AI"),
]


def build_timeline(context: Dict[str, Any]) -> List[TimelineEvent]:
    """Reconstruct the hiring timeline (Module 4)."""
    sources = set(context.get("evidence_sources", []))
    approvals = context.get("approvals", {}) or {}
    events: List[TimelineEvent] = []

    order = 1
    for name, source, actor in _TIMELINE:
        observed = source in sources
        events.append(
            TimelineEvent(
                order=order,
                name=name,
                actor=actor,
                status="Observed" if observed else "Unavailable",
                detail=f"Evidenced by {source}." if observed else f"Not evidenced ({source} absent).",
            )
        )
        order += 1

    # Executive approval (human) — from the approval matrix.
    approval_map = {a["approver"]: a for a in approvals.get("approvals", [])}
    exec_state = approval_map.get("Executive", {}).get("state", "Not Required")
    exec_status = "Observed" if exec_state == "Complete" else "Unavailable"
    events.append(
        TimelineEvent(
            order=order,
            name="Executive approval",
            actor="Human",
            status=exec_status,
            detail=(
                "Executive approval recorded." if exec_state == "Complete"
                else f"Executive approval {exec_state.lower()} (unverified without an approval system)."
            ),
        )
    )
    order += 1

    committee_present = "AI Hiring Committee" in sources
    events.append(
        TimelineEvent(
            order=order,
            name="Final decision",
            actor="Human",
            status="Observed" if committee_present else "Unavailable",
            detail=(
                "Final decision anchored on the committee + governance chain."
                if committee_present else "Final decision not reconstructable without a committee decision."
            ),
        )
    )
    return events
