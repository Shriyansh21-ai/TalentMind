"""Structured schemas for the CompensationGovernanceAgent (Phase 5 / Milestone 1).

The **Enterprise Compensation Governance System** does NOT predict salaries. It
explains, justifies, documents and governs a compensation *recommendation* using
evidence from TalentMind's existing AI ecosystem. Its job is transparency: why is
this compensation recommended, can Finance approve it, can HR defend it, does it
respect policy and internal equity, can executives explain it.

Two families live here:

* :class:`CompensationNarrative` — the single validated :class:`BaseAIResponse`
  the AI Platform agent produces. It is **score-free at the top level** (the
  platform safety guard rejects ``score``/``rating``/``percent``/
  ``confidence_value`` fields), so every element is qualitative prose. All numbers
  live in the nested dataclasses below.
* Dataclasses (:class:`CompensationRange`, :class:`JustificationEntry`,
  :class:`GovernanceCheck`, :class:`MarketPosition`, :class:`OfferScenario`,
  :class:`NegotiationIntelligence`, :class:`BudgetAssessment`,
  :class:`InternalEquityReadiness`, :class:`FutureCompensationOutlook`,
  :class:`Estimate`, :class:`AuditTrail`, :class:`CompensationReport`) — the
  assembled governance artefact the engine produces for the UI / copilot / export.

Every numeric field is a **heuristic estimate or observed evidence**, never a
fabricated market survey (Module 16). The schema is composable so Module 14
extensions (HRIS / Payroll / Workday / currency conversion / equity valuation)
can consume or extend it without a redesign.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class CompensationNarrative(BaseAIResponse):
    """The compensation-governance narrative the agent produces (Modules 1, 10).

    Score-free at the top level; every figure lives in the nested dataclasses.
    Each element restates the structured evidence — it fabricates no salary
    survey, payroll or market data (Module 16).
    """

    executive_summary: str
    recommendation_rationale: str = ""
    market_position_note: str = ""
    governance_note: str = ""
    negotiation_note: str = ""
    budget_note: str = ""
    internal_equity_note: str = ""
    future_outlook_note: str = ""
    transparency_note: str = ""
    key_justifications: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
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
# Shared nested estimate (numbers allowed — nested, not top level)
# ---------------------------------------------------------------------------


@dataclass
class Estimate:
    """A single governance estimate with an explicit confidence + basis.

    ``kind`` records the epistemic register (Module 16): Observed Evidence,
    Heuristic Estimate, Business Recommendation or Assumption.
    """

    label: str = ""
    level: str = "Moderate"
    rationale: str = ""
    confidence: float = 0.0
    kind: str = "Heuristic Estimate"
    basis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the estimate."""
        return {
            "label": self.label,
            "level": self.level,
            "rationale": self.rationale,
            "confidence": round(self.confidence, 1),
            "kind": self.kind,
            "basis": list(self.basis),
        }


# ---------------------------------------------------------------------------
# Module 1 — Compensation recommendation (a defensible RANGE, never a point)
# ---------------------------------------------------------------------------


@dataclass
class CompensationRange:
    """A defensible compensation range (Module 1). Never a single fixed salary."""

    currency: str = "INR"
    unit: str = "LPA"
    minimum: float = 0.0
    target: float = 0.0
    maximum: float = 0.0
    confidence: float = 0.0
    confidence_label: str = "Moderate"
    basis: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the range."""
        return {
            "currency": self.currency,
            "unit": self.unit,
            "minimum": round(self.minimum, 2),
            "target": round(self.target, 2),
            "maximum": round(self.maximum, 2),
            "confidence": round(self.confidence, 1),
            "confidence_label": self.confidence_label,
            "basis": list(self.basis),
            "assumptions": list(self.assumptions),
        }

    def formatted(self) -> str:
        """Return a human-readable range string."""
        return (
            f"{self.currency} {self.minimum:.1f}-{self.maximum:.1f} {self.unit} "
            f"(target {self.target:.1f})"
        )


# ---------------------------------------------------------------------------
# Module 2 — Offer justification (transparent audit trail entries)
# ---------------------------------------------------------------------------


@dataclass
class JustificationEntry:
    """One line of the offer-justification audit trail (Module 2).

    Separates the four registers Module 16 mandates via ``kind``:
    Evidence, Reasoning, Business Impact, Assumption.
    """

    kind: str  # "Evidence" | "Reasoning" | "Business Impact" | "Assumption"
    statement: str
    source: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the justification entry."""
        return {
            "kind": self.kind,
            "statement": self.statement,
            "source": self.source,
            "confidence": round(self.confidence, 1),
        }


# ---------------------------------------------------------------------------
# Module 3 — Compensation governance checks
# ---------------------------------------------------------------------------


@dataclass
class GovernanceCheck:
    """One governance dimension evaluated with an explicit WHY (Module 3)."""

    dimension: str
    status: str = "Aligned"  # Aligned | Review | Not Evaluable
    rationale: str = ""
    source: str = "Compensation Governance"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the governance check."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 4 — Market position
# ---------------------------------------------------------------------------


@dataclass
class MarketPosition:
    """The estimated market position (Module 4). Never fabricates market data."""

    position: str = "Market Competitive"
    rationale: str = ""
    data_available: bool = False
    data_note: str = "Recommendation based on internal heuristic model."
    assumptions: list[str] = field(default_factory=list)
    basis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the market position."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 5 — Offer strategy scenarios
# ---------------------------------------------------------------------------


@dataclass
class OfferScenario:
    """One offer scenario (Module 5): Conservative / Competitive / Premium / Aggressive."""

    name: str
    comp_range: CompensationRange
    advantages: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    negotiation_impact: str = ""
    retention_impact: str = ""
    business_impact: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the scenario."""
        return {
            "name": self.name,
            "comp_range": self.comp_range.to_dict(),
            "advantages": list(self.advantages),
            "risks": list(self.risks),
            "negotiation_impact": self.negotiation_impact,
            "retention_impact": self.retention_impact,
            "business_impact": self.business_impact,
        }


# ---------------------------------------------------------------------------
# Module 6 — Negotiation intelligence
# ---------------------------------------------------------------------------


@dataclass
class NegotiationIntelligence:
    """Negotiation intelligence (Module 6). Separates observed evidence from advice."""

    acceptance_likelihood: str = "Moderate"
    negotiation_probability: str = "Moderate"
    confidence: float = 0.0
    observed_evidence: list[str] = field(default_factory=list)
    likely_objections: list[str] = field(default_factory=list)
    strategy: list[str] = field(default_factory=list)
    fallback_strategy: list[str] = field(default_factory=list)
    executive_approval_notes: list[str] = field(default_factory=list)
    recruiter_talking_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the negotiation intelligence."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 7 — Budget governance
# ---------------------------------------------------------------------------


@dataclass
class BudgetAssessment:
    """Budget governance (Module 7). Never fabricates financial metrics."""

    hire_type: str = "Growth Hire"  # Replacement | Growth | Critical
    budget_utilization: str = "Within Band"
    hiring_priority: str = "Standard"
    investment_rationale: str = ""
    business_justification: str = ""
    confidence: float = 0.0
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the budget assessment."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 8 — Internal equity readiness (HRIS-ready; no payroll connectors)
# ---------------------------------------------------------------------------


@dataclass
class InternalEquityReadiness:
    """Internal equity readiness (Module 8).

    When no company compensation data is available (the default — TalentMind
    ships no payroll connector), ``available`` is False and ``status_message``
    reads "Internal equity validation unavailable." When a future HRIS provider
    is injected, the checks + recommendations are populated.
    """

    available: bool = False
    status_message: str = "Internal equity validation unavailable."
    checks: list[GovernanceCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    hris_interfaces_ready: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the internal-equity readiness."""
        return {
            "available": self.available,
            "status_message": self.status_message,
            "checks": [c.to_dict() for c in self.checks],
            "recommendations": list(self.recommendations),
            "hris_interfaces_ready": list(self.hris_interfaces_ready),
        }


# ---------------------------------------------------------------------------
# Module 9 — Future compensation outlook
# ---------------------------------------------------------------------------


@dataclass
class FutureCompensationOutlook:
    """Future compensation outlook (Module 9). Confidence on every estimate."""

    promotion_readiness: Estimate
    progression: Estimate
    retention_incentives: Estimate
    learning_investment: Estimate
    growth_compensation: Estimate
    long_term_value: Estimate

    def items(self) -> list[tuple]:
        """Return ``(display_name, Estimate)`` pairs in presentation order."""
        return [
            ("Promotion Readiness", self.promotion_readiness),
            ("Compensation Progression", self.progression),
            ("Retention Incentives", self.retention_incentives),
            ("Learning Investment", self.learning_investment),
            ("Career-Growth Compensation", self.growth_compensation),
            ("Long-Term Talent Value", self.long_term_value),
        ]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the outlook."""
        return {
            "promotion_readiness": self.promotion_readiness.to_dict(),
            "progression": self.progression.to_dict(),
            "retention_incentives": self.retention_incentives.to_dict(),
            "learning_investment": self.learning_investment.to_dict(),
            "growth_compensation": self.growth_compensation.to_dict(),
            "long_term_value": self.long_term_value.to_dict(),
        }


# ---------------------------------------------------------------------------
# Module 12 — Transparency audit trail (the flagship)
# ---------------------------------------------------------------------------


@dataclass
class AuditTrail:
    """The exportable transparency audit trail (Module 12 — flagship).

    Records everything a reviewer needs to defend the decision: a decision id,
    the evidence sources, the AI agents consulted, the ordered reasoning chain,
    the confidence, the required approvals, the business justification and the
    human-review status.
    """

    decision_id: str
    decision_timestamp: str
    evidence_sources: list[str] = field(default_factory=list)
    agents_consulted: list[str] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_label: str = "Moderate"
    approvals_required: list[str] = field(default_factory=list)
    business_justification: str = ""
    human_review_status: str = "Pending Human Review"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the audit trail."""
        return {
            "decision_id": self.decision_id,
            "decision_timestamp": self.decision_timestamp,
            "evidence_sources": list(self.evidence_sources),
            "agents_consulted": list(self.agents_consulted),
            "reasoning_chain": list(self.reasoning_chain),
            "confidence": round(self.confidence, 1),
            "confidence_label": self.confidence_label,
            "approvals_required": list(self.approvals_required),
            "business_justification": self.business_justification,
            "human_review_status": self.human_review_status,
        }

    def to_export_text(self) -> str:
        """Render the audit trail as a portable, human-readable plaintext report."""

        def _block(items: list[str]) -> list[str]:
            return items or ["  (none)"]

        lines = [
            "TALENTMIND - COMPENSATION DECISION AUDIT TRAIL",
            "=" * 52,
            f"Decision ID        : {self.decision_id}",
            f"Timestamp          : {self.decision_timestamp or 'n/a'}",
            f"Confidence         : {self.confidence_label} ({self.confidence:.0f}/100)",
            f"Human Review       : {self.human_review_status}",
            "",
            "Evidence Sources:",
            *_block([f"  - {s}" for s in self.evidence_sources]),
            "",
            "AI Agents Consulted:",
            *_block([f"  - {a}" for a in self.agents_consulted]),
            "",
            "Reasoning Chain:",
            *_block([f"  {i}. {step}" for i, step in enumerate(self.reasoning_chain, start=1)]),
            "",
            "Approvals Required:",
            *_block([f"  - {a}" for a in self.approvals_required]),
            "",
            "Business Justification:",
            f"  {self.business_justification or 'n/a'}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Assembled governance report artefact
# ---------------------------------------------------------------------------


@dataclass
class CompensationReport:
    """The unified compensation governance report (Modules 1-12).

    Aggregates the recommendation range, offer justification, governance checks,
    market position, offer scenarios, negotiation intelligence, budget
    assessment, internal-equity readiness, future outlook, the narrative, charts
    and — the flagship — the transparency audit trail. It stores upstream signals
    verbatim and adds only governance synthesis; it never recomputes an engine and
    never fabricates financial data (Modules 15 / 16).
    """

    report_id: str
    candidate_id: str
    generated_on: str
    candidate_overview: dict[str, Any]
    narrative: CompensationNarrative
    recommended_range: CompensationRange
    justification: list[JustificationEntry]
    governance_checks: list[GovernanceCheck]
    market_position: MarketPosition
    scenarios: list[OfferScenario]
    negotiation: NegotiationIntelligence
    budget: BudgetAssessment
    internal_equity: InternalEquityReadiness
    future_outlook: FutureCompensationOutlook
    audit_trail: AuditTrail
    charts: dict[str, Any] = field(default_factory=dict)
    evidence_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "report_id": self.report_id,
            "candidate_id": self.candidate_id,
            "generated_on": self.generated_on,
            "candidate_overview": self.candidate_overview,
            "narrative": self.narrative.to_dict(),
            "recommended_range": self.recommended_range.to_dict(),
            "justification": [j.to_dict() for j in self.justification],
            "governance_checks": [g.to_dict() for g in self.governance_checks],
            "market_position": self.market_position.to_dict(),
            "scenarios": [s.to_dict() for s in self.scenarios],
            "negotiation": self.negotiation.to_dict(),
            "budget": self.budget.to_dict(),
            "internal_equity": self.internal_equity.to_dict(),
            "future_outlook": self.future_outlook.to_dict(),
            "audit_trail": self.audit_trail.to_dict(),
            "charts": self.charts,
            "evidence_sources": list(self.evidence_sources),
            "warnings": list(self.warnings),
        }
