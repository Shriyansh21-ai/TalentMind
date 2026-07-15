"""Structured schemas for the PayEquityGuardianAgent (Phase 5 / Milestone 2).

The **Enterprise Internal Pay Equity & Fairness Intelligence System** answers: is
this offer internally fair, will it create salary compression, could it create
promotion inequity, does it align with company pay philosophy, and should
executives review it. It is **not** a bias detector and **not** a legal decision
engine (Module 14): it never fabricates payroll or protected characteristics,
never accuses discrimination and never concludes a legal violation — it only
surfaces governance risks and areas requiring human review.

Two families live here:

* :class:`PayEquityNarrative` — the single validated :class:`BaseAIResponse` the
  AI Platform agent produces. **Score-free at the top level** (the platform safety
  guard rejects ``score``/``rating``/``percent``/``confidence_value`` fields).
* Dataclasses (:class:`EquityFinding`, :class:`CompressionAssessment`,
  :class:`InversionAssessment`, :class:`PromotionEquityAssessment`,
  :class:`PolicyAlignment`, :class:`FairnessAssessment`, :class:`ApprovalRequirement`,
  :class:`ExecutiveReview`, :class:`EquityScenario`, :class:`EquityRisk`,
  :class:`PayEquityReport`) — the assembled fairness artefact for the UI / copilot.

Every conclusion carries an epistemic register: Observed Evidence, Unavailable
Data, Heuristic, Recommendation or Human Review (Module 14). The schema is
composable so Module 12 HRIS integrations can extend it without a redesign.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# The epistemic registers every finding must declare (Module 14).
REGISTERS = ("Observed Evidence", "Unavailable Data", "Heuristic", "Recommendation", "Human Review")


# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class PayEquityNarrative(BaseAIResponse):
    """The pay-equity fairness narrative the agent produces (Modules 1, 6, 9).

    Score-free at the top level; every element is qualitative prose. It surfaces
    governance risks and review needs only — never a legal conclusion or a
    discrimination accusation (Module 14).
    """

    executive_summary: str
    equity_assessment: str = ""
    compression_note: str = ""
    inversion_note: str = ""
    promotion_note: str = ""
    policy_note: str = ""
    fairness_note: str = ""
    review_note: str = ""
    data_availability_note: str = ""
    key_findings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    human_review_recommendations: List[str] = Field(default_factory=list)
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
# Module 1 — Internal pay equity findings
# ---------------------------------------------------------------------------


@dataclass
class EquityFinding:
    """One internal-equity dimension evaluated with an explicit WHY (Module 1)."""

    dimension: str
    status: str = "Not Evaluable"  # Consistent | Review | Not Evaluable
    rationale: str = ""
    register: str = "Unavailable Data"
    source: str = "Pay Equity Guardian"

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the finding."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 2 — Salary compression
# ---------------------------------------------------------------------------


@dataclass
class CompressionAssessment:
    """Salary-compression risk (Module 2). Never fabricates payroll."""

    risk_level: str = "Unavailable"  # Low | Medium | High | Unavailable
    data_available: bool = False
    rationale: str = "Company compensation data unavailable."
    business_impact: str = ""
    mitigation: str = ""
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the compression assessment."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 3 — Pay inversion
# ---------------------------------------------------------------------------


@dataclass
class InversionCase:
    """A single potential pay-inversion case (peers anonymized to an id)."""

    peer_ref: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InversionAssessment:
    """Pay-inversion risk (Module 3). Only evaluable with internal data."""

    risk_level: str = "Unavailable"  # Low | Medium | High | Unavailable
    data_available: bool = False
    rationale: str = "Unable to evaluate without internal compensation data."
    cases: List[InversionCase] = field(default_factory=list)
    business_impact: str = ""
    recommended_review: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the inversion assessment."""
        return {
            "risk_level": self.risk_level,
            "data_available": self.data_available,
            "rationale": self.rationale,
            "cases": [c.to_dict() for c in self.cases],
            "business_impact": self.business_impact,
            "recommended_review": self.recommended_review,
        }


# ---------------------------------------------------------------------------
# Module 4 — Promotion equity
# ---------------------------------------------------------------------------


@dataclass
class PromotionEquityAssessment:
    """Promotion-equity evaluation (Module 4)."""

    consistency: str = "Not Evaluable"  # Consistent | Review | Not Evaluable
    data_available: bool = False
    level_alignment: str = ""
    progression_note: str = ""
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the promotion-equity assessment."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 5 — Policy alignment
# ---------------------------------------------------------------------------


@dataclass
class PolicyAlignment:
    """Compensation-policy alignment (Module 5). Policy — never legal."""

    policy_key: str = ""
    policy_name: str = ""
    alignment: str = "Not Evaluable"  # Aligned | Partial | Violation | Not Evaluable
    rationale: str = ""
    violations: List[str] = field(default_factory=list)
    review_requirements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the policy alignment."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 6 — Fairness intelligence
# ---------------------------------------------------------------------------


@dataclass
class FairnessAssessment:
    """Fairness intelligence (Module 6). Identifies review areas, not legal facts."""

    assessment: str = ""
    concerns: List[str] = field(default_factory=list)
    human_review_recommendations: List[str] = field(default_factory=list)
    governance_notes: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the fairness assessment."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 7 — Executive review
# ---------------------------------------------------------------------------


@dataclass
class ApprovalRequirement:
    """One approver's requirement in the review chain (Module 7)."""

    approver: str
    required: bool = False
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutiveReview:
    """The executive-review determination (Module 7)."""

    review_level: str = "Standard"  # Standard | Elevated | Executive
    approvals: List[ApprovalRequirement] = field(default_factory=list)
    rationale: str = ""

    def required_approvers(self) -> List[str]:
        """Return the approvers that are required."""
        return [a.approver for a in self.approvals if a.required]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the executive review."""
        return {
            "review_level": self.review_level,
            "approvals": [a.to_dict() for a in self.approvals],
            "rationale": self.rationale,
            "required_approvers": self.required_approvers(),
        }


# ---------------------------------------------------------------------------
# Module 8 — Scenario simulation
# ---------------------------------------------------------------------------


@dataclass
class EquityScenario:
    """One equity scenario (Module 8): current vs. alternative offers."""

    name: str
    offer_target: float = 0.0
    currency: str = "INR"
    unit: str = "LPA"
    equity_impact: str = ""
    budget_impact: str = ""
    promotion_impact: str = ""
    retention_impact: str = ""
    tradeoffs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the scenario."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Equity risk (gauge)
# ---------------------------------------------------------------------------


@dataclass
class EquityRisk:
    """Overall internal-equity risk (feeds the Module 10 gauge)."""

    level: str = "Unknown"  # Low | Medium | High | Unknown
    drivers: List[str] = field(default_factory=list)
    confidence: float = 0.0
    data_available: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the equity risk."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Assembled report artefact
# ---------------------------------------------------------------------------


@dataclass
class PayEquityReport:
    """The unified pay-equity governance report (Modules 1-10).

    Aggregates the internal-equity findings, compression, inversion, promotion
    equity, policy alignment, fairness assessment, executive review, scenarios and
    the overall equity risk — every one derived from existing intelligence and the
    (optional) injected HRIS data. It stores upstream signals verbatim, adds only
    fairness synthesis, and never fabricates payroll or concludes a legal violation
    (Modules 13 / 14).
    """

    report_id: str
    candidate_id: str
    generated_on: str
    policy_key: str
    data_available: bool
    candidate_overview: Dict[str, Any]
    offer_summary: Dict[str, Any]
    narrative: PayEquityNarrative
    equity_risk: EquityRisk
    equity_findings: List[EquityFinding]
    compression: CompressionAssessment
    inversion: InversionAssessment
    promotion: PromotionEquityAssessment
    policy_alignment: PolicyAlignment
    fairness: FairnessAssessment
    executive_review: ExecutiveReview
    scenarios: List[EquityScenario]
    charts: Dict[str, Any] = field(default_factory=dict)
    evidence_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "report_id": self.report_id,
            "candidate_id": self.candidate_id,
            "generated_on": self.generated_on,
            "policy_key": self.policy_key,
            "data_available": self.data_available,
            "candidate_overview": self.candidate_overview,
            "offer_summary": self.offer_summary,
            "narrative": self.narrative.to_dict(),
            "equity_risk": self.equity_risk.to_dict(),
            "equity_findings": [f.to_dict() for f in self.equity_findings],
            "compression": self.compression.to_dict(),
            "inversion": self.inversion.to_dict(),
            "promotion": self.promotion.to_dict(),
            "policy_alignment": self.policy_alignment.to_dict(),
            "fairness": self.fairness.to_dict(),
            "executive_review": self.executive_review.to_dict(),
            "scenarios": [s.to_dict() for s in self.scenarios],
            "charts": self.charts,
            "evidence_sources": list(self.evidence_sources),
            "warnings": list(self.warnings),
        }
