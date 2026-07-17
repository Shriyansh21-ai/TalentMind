"""Approval governance (Module 2).

Determines which approvals are required and whether each is complete, explaining
**why** each approval is or is not required. The *required* set + reasons are
reused from the Pay Equity Guardian's executive review (no duplicated reasoning);
*completion* state comes from an optional injected approval provider. Without a
provider, required approvals are "Requires Review" (not assumed complete)
(Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import ApprovalMatrix, ApprovalStatus
from src.ai.agents.compliance.templates import APPROVER_ROLES


def build_approval_matrix(context: dict[str, Any], provider: Any) -> ApprovalMatrix:
    """Build the approval matrix (Module 2)."""
    required = set(context.get("required_approvers", []))
    reasons: dict[str, str] = context.get("approval_reasons", {}) or {}

    provider_state: dict[str, dict[str, Any]] = {}
    has_provider = provider is not None and getattr(provider, "is_available", lambda: False)()
    if has_provider:
        provider_state = provider.get_approvals(context.get("candidate_id", "")) or {}

    approvals = []
    for role in APPROVER_ROLES:
        is_required = role in required
        reason = reasons.get(role) or (
            f"{role} approval required by the pay-equity/governance review."
            if is_required
            else f"{role} approval not required by the pay-equity/governance review."
        )
        rec = provider_state.get(role) if has_provider else None

        # The provider's recorded approval is authoritative for completion state,
        # even for roles the pay-equity review did not itself require (a company
        # policy may still require them).
        if rec is not None:
            state = "Complete" if rec.get("approved") else "Missing"
            if rec.get("approved") and rec.get("by"):
                reason += f" Approved by {rec['by']}."
        elif is_required and has_provider:
            state = "Missing"
            reason += " No approval recorded in the connected system."
        elif is_required:
            state = "Requires Review"
            reason += " No approval system connected — completion cannot be confirmed."
        else:
            state = "Not Required"

        approvals.append(
            ApprovalStatus(approver=role, required=is_required, state=state, reason=reason)
        )

    return ApprovalMatrix(approvals=approvals)
