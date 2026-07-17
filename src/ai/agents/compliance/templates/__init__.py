"""Hiring-compliance configuration (Modules 1, 3, 4, 12).

Pure configuration (no engine / UI import) shared across the compliance modules:

* :data:`COMPLIANCE_POLICIES` — the **configurable** company governance policies
  (executive hires need committee approval, critical hires need executive review,
  salary above a threshold needs finance approval, remote hires need extra
  documentation). These are data entries, never hardcoded logic (Module 3); a
  caller may inject a custom :class:`CompliancePolicy`.
* :data:`WORKFLOW_STEPS` — the required hiring-workflow steps and the evidence key
  that satisfies each (Module 1).
* :data:`REQUIRED_DOCUMENTS` — the documents whose presence is validated (Module 4).
* :data:`COMPLIANCE_FRAMEWORKS` — the *names* of the external governance frameworks
  / systems the provider interface is designed for (Module 12). No integration is
  implemented — an extension-point registry only.

Adding a policy, workflow step, document or framework is a one-entry data change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class CompliancePolicy:
    """A configurable company governance policy (Module 3 — data, not code).

    Attributes:
        key: Stable policy key.
        name: Human-readable policy name.
        description: One-line statement of the rule.
        applies_when: A context condition token the engine understands
            (``executive_hire`` | ``critical_hire`` | ``salary_above_threshold`` |
            ``remote_hire`` | ``always``).
        requires: The control token that must be satisfied
            (``committee_complete`` | ``executive_approval`` | ``finance_approval`` |
            ``extra_documentation``).
    """

    key: str
    name: str
    description: str
    applies_when: str
    requires: str


COMPLIANCE_POLICIES: dict[str, CompliancePolicy] = {
    "exec_hire_committee": CompliancePolicy(
        key="exec_hire_committee",
        name="Executive Hire -> Committee",
        description="Executive/critical hires require a completed hiring-committee decision.",
        applies_when="executive_hire",
        requires="committee_complete",
    ),
    "critical_hire_exec": CompliancePolicy(
        key="critical_hire_exec",
        name="Critical Hire -> Executive Review",
        description="Critical hires require executive review/approval.",
        applies_when="critical_hire",
        requires="executive_approval",
    ),
    "salary_threshold_finance": CompliancePolicy(
        key="salary_threshold_finance",
        name="Above-Threshold Salary -> Finance",
        description="Offers above the finance threshold require finance approval.",
        applies_when="salary_above_threshold",
        requires="finance_approval",
    ),
    "remote_documentation": CompliancePolicy(
        key="remote_documentation",
        name="Remote Hire -> Extra Documentation",
        description="Remote hires require additional documentation.",
        applies_when="remote_hire",
        requires="extra_documentation",
    ),
}

DEFAULT_POLICY_SET = list(COMPLIANCE_POLICIES.keys())

# Configurable thresholds (never hardcoded in logic).
COMPLIANCE_THRESHOLDS = {
    "finance_salary_threshold_lpa": 50.0,
}


def get_policy(key: str) -> CompliancePolicy:
    """Return the compliance policy for ``key`` (raises KeyError-safe via get)."""
    return COMPLIANCE_POLICIES[key]


def list_policies() -> list[CompliancePolicy]:
    """Return every registered compliance policy (stable order)."""
    return list(COMPLIANCE_POLICIES.values())


@dataclass(frozen=True)
class WorkflowStepDef:
    """A required hiring-workflow step (Module 1)."""

    key: str
    name: str
    evidence_source: str  # the evidence-source label that satisfies this step
    critical: bool = True


# Ordered required workflow steps. ``evidence_source`` matches the labels the
# upstream engines report, so presence is derived, never fabricated.
WORKFLOW_STEPS: list[WorkflowStepDef] = [
    WorkflowStepDef("resume_screen", "Resume screened", "Resume Analyst Agent"),
    WorkflowStepDef("jd_defined", "Job description defined", "JD Analyst Agent", critical=False),
    WorkflowStepDef("interview", "Interview completed", "Interview Intelligence"),
    WorkflowStepDef("committee", "Committee decision", "AI Hiring Committee"),
    WorkflowStepDef("compensation", "Compensation review", "Compensation Governance Agent"),
    WorkflowStepDef("pay_equity", "Pay-equity review", "Pay Equity Guardian"),
    WorkflowStepDef("approvals", "Required approvals complete", "__approvals__"),
    WorkflowStepDef("documentation", "Documentation complete", "__documentation__"),
]


@dataclass(frozen=True)
class DocumentDef:
    """A document whose presence is validated (Module 4)."""

    key: str
    name: str
    evidence_source: str = ""  # label that confirms presence (empty = provider-only)


REQUIRED_DOCUMENTS: list[DocumentDef] = [
    DocumentDef("resume", "Resume", "Resume Analyst Agent"),
    DocumentDef("job_description", "Job Description", "JD Analyst Agent"),
    DocumentDef("interview_notes", "Interview Notes", "Interview Intelligence"),
    DocumentDef("committee_decision", "Committee Decision", "AI Hiring Committee"),
    DocumentDef("compensation_report", "Compensation Report", "Compensation Governance Agent"),
    DocumentDef("pay_equity_report", "Pay Equity Report", "Pay Equity Guardian"),
    DocumentDef("executive_report", "Executive Report", ""),
    DocumentDef("interview_packet", "Interview Packet", ""),
]

# Module 12 — extension-point registry. Frameworks / systems the provider
# interface is DESIGNED for; none is implemented.
COMPLIANCE_FRAMEWORKS: list[str] = [
    "ISO 30414",
    "SOC 2",
    "Internal Governance System",
    "Document Management System",
    "HR Policy Engine",
    "Workflow System",
]

# The full approver ladder the compliance layer reasons over.
APPROVER_ROLES: list[str] = ["Recruiter", "Hiring Manager", "HR", "Finance", "Legal", "Executive"]
