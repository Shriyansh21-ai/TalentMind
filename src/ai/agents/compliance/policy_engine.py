"""Policy compliance (Module 3).

Evaluates the offer/workflow against **configurable** company governance policies
(``templates.COMPLIANCE_POLICIES``; a custom :class:`CompliancePolicy` may be
injected). Each policy declares an ``applies_when`` context condition and a
``requires`` control; the engine checks the control against the observed evidence.
Policy conclusions are governance findings — never legal opinions (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import ApprovalMatrix, PolicyCheck
from src.ai.agents.compliance.templates import CompliancePolicy


def _applies(policy: CompliancePolicy, context: dict[str, Any]) -> bool:
    """Return whether a policy's ``applies_when`` condition holds in the context."""
    cond = policy.applies_when
    if cond == "always":
        return True
    if cond == "executive_hire":
        return bool(context.get("executive_hire"))
    if cond == "critical_hire":
        return bool(context.get("critical_hire"))
    if cond == "salary_above_threshold":
        return bool(context.get("salary_above_threshold"))
    if cond == "remote_hire":
        return bool(context.get("remote_hire"))
    return False


def _control_state(
    policy: CompliancePolicy, context: dict[str, Any], approvals: ApprovalMatrix
) -> tuple:
    """Return ``(status, rationale, actions)`` for a policy's required control."""
    sources = set(context.get("evidence_sources", []))
    req = policy.requires

    if req == "committee_complete":
        if "AI Hiring Committee" in sources:
            return "Compliant", "A completed committee decision is on file.", []
        return (
            "Violation",
            "Policy requires a committee decision, which is not evidenced.",
            ["Convene the hiring committee before proceeding."],
        )

    approval_map = {a.approver: a for a in approvals.approvals}
    if req in ("executive_approval", "finance_approval"):
        role = "Executive" if req == "executive_approval" else "Finance"
        status_obj = approval_map.get(role)
        if status_obj and status_obj.state == "Complete":
            return "Compliant", f"{role} approval is complete.", []
        if status_obj and status_obj.state == "Requires Review":
            return (
                "Requires Review",
                f"{role} approval cannot be confirmed without an approval system.",
                [f"Confirm {role} approval."],
            )
        return (
            "Violation",
            f"Policy requires {role} approval, which is missing.",
            [f"Obtain {role} approval."],
        )

    if req == "extra_documentation":
        return (
            "Requires Review",
            "Remote hire requires additional documentation; presence cannot be confirmed without a document source.",
            ["Confirm remote-hire documentation is filed."],
        )

    return "Not Evaluable", "No evaluable control mapped to this policy.", []


def evaluate_policies(
    policies: list[CompliancePolicy],
    context: dict[str, Any],
    approvals: ApprovalMatrix,
) -> list[PolicyCheck]:
    """Evaluate each configured policy against the context (Module 3)."""
    checks: list[PolicyCheck] = []
    for policy in policies:
        if not _applies(policy, context):
            checks.append(
                PolicyCheck(
                    policy_key=policy.key,
                    policy_name=policy.name,
                    status="Not Applicable",
                    rationale=f"'{policy.description}' does not apply to this hire.",
                    required_actions=[],
                )
            )
            continue
        status, rationale, actions = _control_state(policy, context, approvals)
        checks.append(
            PolicyCheck(
                policy_key=policy.key,
                policy_name=policy.name,
                status=status,
                rationale=f"{policy.description} {rationale}",
                required_actions=actions,
            )
        )
    return checks
