"""Structured schemas for the HiringComplianceAgent (Phase 5 / Milestone 3).

The **Enterprise Hiring Compliance Intelligence System** answers whether a hiring
workflow follows company governance: are required approvals complete, are
mandatory steps missing, does the process satisfy internal policy, and should
Legal or Compliance review it. It is **not** a legal-advice system and **not** a
law engine (Module 14): it never gives a legal opinion, never interprets
employment law and never fabricates a compliance conclusion — it identifies
governance risks and areas requiring human review.

Two families live here:

* :class:`ComplianceNarrative` — the single validated :class:`BaseAIResponse` the
  AI Platform agent produces. **Score-free at the top level**.
* Dataclasses (:class:`WorkflowStep`, :class:`WorkflowCompliance`,
  :class:`ApprovalStatus`, :class:`ApprovalMatrix`, :class:`PolicyCheck`,
  :class:`DocumentStatus`, :class:`DocumentationReview`, :class:`AuditFinding`,
  :class:`AuditTrailValidation`, :class:`ComplianceException`,
  :class:`GovernanceRisk`, :class:`ComplianceScenario`, :class:`ComplianceReview`,
  :class:`HiringComplianceReport`) — the assembled governance artefact.

Every conclusion carries an epistemic register: Observed Evidence, Company Policy,
Missing Information, Recommendation or Human Review (Module 14).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

REGISTERS = (
    "Observed Evidence",
    "Company Policy",
    "Missing Information",
    "Recommendation",
    "Human Review",
)


# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class ComplianceNarrative(BaseAIResponse):
    """The hiring-compliance narrative the agent produces (Modules 1, 5, 8).

    Score-free at the top level; every element is qualitative prose. It surfaces
    governance status and review needs only — never legal advice, an employment-law
    interpretation or a regulatory ruling (Module 14).
    """

    executive_summary: str
    workflow_note: str = ""
    approval_note: str = ""
    policy_note: str = ""
    documentation_note: str = ""
    audit_note: str = ""
    risk_note: str = ""
    required_actions: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    human_review_recommendations: list[str] = Field(default_factory=list)
    confidence_note: str = ""

    @field_validator("executive_summary")
    @classmethod
    def _summary_non_empty(cls, value: str) -> str:
        """Ensure the executive summary is a non-empty string."""
        text = (value or "").strip()
        if not text:
            raise ValueError("executive_summary must not be empty")
        return text


# ---------------------------------------------------------------------------
# Module 1 — Workflow compliance
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """One required workflow step evaluated with an explicit WHY (Module 1)."""

    name: str
    status: str = "Requires Review"  # Completed | Missing | Requires Review
    rationale: str = ""
    register: str = "Missing Information"
    critical: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowCompliance:
    """Overall hiring-workflow compliance (Module 1)."""

    steps: list[WorkflowStep] = field(default_factory=list)
    completed: int = 0
    total: int = 0
    status: str = "Requires Review"  # Compliant | Incomplete | Requires Review
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "completed": self.completed,
            "total": self.total,
            "status": self.status,
            "confidence": round(self.confidence, 1),
        }


# ---------------------------------------------------------------------------
# Module 2 — Approval governance
# ---------------------------------------------------------------------------


@dataclass
class ApprovalStatus:
    """One approver's requirement + completion state (Module 2)."""

    approver: str
    required: bool = False
    state: str = "Not Required"  # Complete | Missing | Requires Review | Not Required
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalMatrix:
    """The approval matrix (Module 2)."""

    approvals: list[ApprovalStatus] = field(default_factory=list)

    def required(self) -> list[str]:
        return [a.approver for a in self.approvals if a.required]

    def outstanding(self) -> list[str]:
        return [
            a.approver
            for a in self.approvals
            if a.required and a.state in ("Missing", "Requires Review")
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvals": [a.to_dict() for a in self.approvals],
            "required": self.required(),
            "outstanding": self.outstanding(),
        }


# ---------------------------------------------------------------------------
# Module 3 — Policy compliance
# ---------------------------------------------------------------------------


@dataclass
class PolicyCheck:
    """One configurable policy evaluated with an explicit WHY (Module 3)."""

    policy_key: str
    policy_name: str
    status: str = (
        "Not Applicable"  # Compliant | Violation | Requires Review | Not Applicable | Not Evaluable
    )
    rationale: str = ""
    required_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 4 — Documentation validation
# ---------------------------------------------------------------------------


@dataclass
class DocumentStatus:
    """One document's presence state (Module 4)."""

    name: str
    state: str = "Requires Review"  # Present | Missing | Requires Review
    register: str = "Missing Information"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentationReview:
    """The documentation review (Module 4)."""

    documents: list[DocumentStatus] = field(default_factory=list)

    def missing(self) -> list[str]:
        return [d.name for d in self.documents if d.state == "Missing"]

    def present(self) -> list[str]:
        return [d.name for d in self.documents if d.state == "Present"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents": [d.to_dict() for d in self.documents],
            "missing": self.missing(),
            "present": self.present(),
        }


# ---------------------------------------------------------------------------
# Module 6 — Audit trail validation
# ---------------------------------------------------------------------------


@dataclass
class AuditFinding:
    """One audit-trail dimension evaluated (Module 6)."""

    dimension: str
    status: str = "Needs Investigation"  # Complete | Incomplete | Needs Investigation
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditTrailValidation:
    """The audit-trail validation (Module 6)."""

    findings: list[AuditFinding] = field(default_factory=list)
    status: str = "Needs Investigation"  # Complete | Incomplete | Needs Investigation

    def to_dict(self) -> dict[str, Any]:
        return {"findings": [f.to_dict() for f in self.findings], "status": self.status}


# ---------------------------------------------------------------------------
# Module 7 — Compliance exceptions
# ---------------------------------------------------------------------------


@dataclass
class ComplianceException:
    """A structured compliance exception (Module 7)."""

    kind: str
    severity: str = "Medium"  # Low | Medium | High
    detail: str = ""
    recommendation: str = ""
    register: str = "Missing Information"
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 5 — Governance risk
# ---------------------------------------------------------------------------


@dataclass
class GovernanceRisk:
    """Overall governance risk (Module 5)."""

    level: str = "Medium"  # Low | Medium | High
    drivers: list[str] = field(default_factory=list)
    missing_controls: list[str] = field(default_factory=list)
    human_review_recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 9 — Scenario simulation
# ---------------------------------------------------------------------------


@dataclass
class ComplianceScenario:
    """One governance scenario simulation (Module 9)."""

    name: str
    governance_impact: str = ""
    affected_controls: list[str] = field(default_factory=list)
    severity: str = "Medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Review determination
# ---------------------------------------------------------------------------


@dataclass
class ComplianceReview:
    """Whether Legal / Compliance should review the hiring decision."""

    legal_review_recommended: bool = False
    compliance_review_recommended: bool = False
    reviewers: list[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Assembled report artefact (Module 8)
# ---------------------------------------------------------------------------


@dataclass
class HiringComplianceReport:
    """The unified hiring-compliance report (Modules 1-10).

    Aggregates the workflow compliance, approval matrix, policy checks,
    documentation review, audit-trail validation, governance risk, exceptions,
    review determination and scenarios — every one derived from existing
    intelligence and the (optional) injected governance data. It never fabricates a
    document or a compliance conclusion and gives no legal advice (Modules 13 / 14).
    """

    report_id: str
    candidate_id: str
    generated_on: str
    data_available: bool
    candidate_overview: dict[str, Any]
    narrative: ComplianceNarrative
    workflow: WorkflowCompliance
    approvals: ApprovalMatrix
    policy_checks: list[PolicyCheck]
    documentation: DocumentationReview
    audit: AuditTrailValidation
    governance_risk: GovernanceRisk
    exceptions: list[ComplianceException]
    review: ComplianceReview
    scenarios: list[ComplianceScenario]
    charts: dict[str, Any] = field(default_factory=dict)
    evidence_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "report_id": self.report_id,
            "candidate_id": self.candidate_id,
            "generated_on": self.generated_on,
            "data_available": self.data_available,
            "candidate_overview": self.candidate_overview,
            "narrative": self.narrative.to_dict(),
            "workflow": self.workflow.to_dict(),
            "approvals": self.approvals.to_dict(),
            "policy_checks": [p.to_dict() for p in self.policy_checks],
            "documentation": self.documentation.to_dict(),
            "audit": self.audit.to_dict(),
            "governance_risk": self.governance_risk.to_dict(),
            "exceptions": [e.to_dict() for e in self.exceptions],
            "review": self.review.to_dict(),
            "scenarios": [s.to_dict() for s in self.scenarios],
            "charts": self.charts,
            "evidence_sources": list(self.evidence_sources),
            "warnings": list(self.warnings),
        }
