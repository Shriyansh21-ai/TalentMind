"""Human review / human-decision extraction (Module 5 support).

Extracts the *human* decisions in the hiring journey from the reused approval
matrix, mapping each approver role to its decision kind and status. Kept separate
from the AI-decision side so responsibility is never blurred (Module 5). Human
approvals that cannot be confirmed without an approval system are marked
Unverified — never assumed to have occurred (Module 14).
"""

from __future__ import annotations

from typing import Any, Dict, List

from src.ai.agents.audit.schemas import DecisionResponsibility

# Map an approver role to the responsibility kind it represents (Module 5).
_ROLE_KIND = {
    "Recruiter": "Recruiter action",
    "Hiring Manager": "Hiring Manager action",
    "HR": "Human override",
    "Finance": "Human override",
    "Legal": "Human override",
    "Executive": "Executive approval",
}


def _status_for(state: str) -> str:
    """Map an approval state to a responsibility status."""
    if state == "Complete":
        return "Observed"
    if state in ("Requires Review",):
        return "Unverified"
    return "Unavailable"


def build_human_decisions(context: Dict[str, Any]) -> List[DecisionResponsibility]:
    """Return the human decision points from the approval matrix (Module 5)."""
    approvals = context.get("approvals", {}) or {}
    decisions: List[DecisionResponsibility] = []
    for a in approvals.get("approvals", []):
        if not a.get("required"):
            continue
        role = a["approver"]
        decisions.append(
            DecisionResponsibility(
                decision=f"{role} approval",
                kind=_ROLE_KIND.get(role, "Human override"),
                responsible_party=role,
                status=_status_for(a.get("state", "")),
                detail=a.get("reason", ""),
            )
        )
    if not decisions:
        decisions.append(
            DecisionResponsibility(
                decision="Human approvals",
                kind="Human override",
                responsible_party="Human",
                status="Unavailable",
                detail="No required human approvals determined / no approval system connected.",
            )
        )
    return decisions
