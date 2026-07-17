"""Structured schemas for the ExecutiveHiringReportAgent (Phase 4 / Milestone 4).

The Executive Decision Layer transforms every structured intelligence artefact
TalentMind already produces into a boardroom-grade hiring report. It creates **no
new hiring logic and no new ranking** — it consumes existing outputs and restates
them for executives (Module 16 Safety).

Two families live here:

* :class:`ExecutiveNarrative` — the single validated :class:`BaseAIResponse` the
  AI Platform agent produces. It is **score-free at the top level** (the platform
  safety guard rejects ``score``/``rating``/``percent``/``confidence_value``
  fields), so every numeric estimate lives in the nested :class:`Estimate` model.
* Dataclasses (:class:`BusinessIntelligence`, :class:`InterviewStrategy`,
  :class:`ExecutiveActionPlan`, :class:`ProvenanceEntry`, :class:`ExecutiveHiringReport`)
  — the assembled report artefact the builder produces for the UI / copilot /
  export engine. This mirrors the committee's ``CommitteeReport`` pattern.

The schema is deliberately composable so Module 17 extensions (Offer Letter,
Salary Report, Candidate Portfolio, Hiring Analytics, Executive/Organization
Dashboards) can consume or extend it without a redesign.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# ---------------------------------------------------------------------------
# Nested estimate model (numbers live here, never at the report's top level)
# ---------------------------------------------------------------------------


class Estimate(BaseAIResponse):
    """A single business-intelligence estimate with an explicit confidence.

    Numbers are permitted because this is a *nested* model — the platform safety
    guard only forbids score-like fields at the top level of an agent's output.
    Every estimate must cite the evidence it rests on (Module 9 / 16).
    """

    label: str = ""
    level: str = "Moderate"
    rationale: str = ""
    confidence: float = 0.0
    basis: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the estimate."""
        return {
            "label": self.label,
            "level": self.level,
            "rationale": self.rationale,
            "confidence": round(self.confidence, 1),
            "basis": list(self.basis),
        }


# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class ExecutiveNarrative(BaseAIResponse):
    """The executive one-page narrative the agent produces (Module 2).

    Score-free at the top level; ``overall_recommendation`` and
    ``executive_confidence`` are qualitative labels, never numbers. Every element
    restates the structured evidence — it invents no conclusions (Module 16).
    """

    executive_summary: str
    overall_recommendation: str = "Proceed to Interview"
    business_impact: str = ""
    technical_impact: str = ""
    leadership_potential: str = ""
    risk_overview: str = ""
    interview_readiness: str = ""
    executive_confidence: str = ""
    top_reasons: list[str] = Field(default_factory=list)
    top_concerns: list[str] = Field(default_factory=list)
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
# Assembled report artefact (dataclasses — engine output for UI / export)
# ---------------------------------------------------------------------------


@dataclass
class BusinessIntelligence:
    """Executive business-impact estimates (Module 9). Confidence on every item."""

    business_impact: Estimate
    productivity: Estimate
    technical_contribution: Estimate
    leadership_contribution: Estimate
    innovation_potential: Estimate
    growth_potential: Estimate
    knowledge_risk: Estimate
    team_impact: Estimate

    def items(self) -> list[tuple]:
        """Return ``(display_name, Estimate)`` pairs in presentation order."""
        return [
            ("Business Impact", self.business_impact),
            ("Expected Productivity", self.productivity),
            ("Technical Contribution", self.technical_contribution),
            ("Leadership Contribution", self.leadership_contribution),
            ("Innovation Potential", self.innovation_potential),
            ("Growth Potential", self.growth_potential),
            ("Knowledge Risk", self.knowledge_risk),
            ("Team Impact", self.team_impact),
        ]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of every estimate."""
        return {
            "business_impact": self.business_impact.to_dict(),
            "productivity": self.productivity.to_dict(),
            "technical_contribution": self.technical_contribution.to_dict(),
            "leadership_contribution": self.leadership_contribution.to_dict(),
            "innovation_potential": self.innovation_potential.to_dict(),
            "growth_potential": self.growth_potential.to_dict(),
            "knowledge_risk": self.knowledge_risk.to_dict(),
            "team_impact": self.team_impact.to_dict(),
        }


@dataclass
class InterviewStrategy:
    """Executive interview roadmap + rubric (Module 7). Sourced from the plan."""

    roadmap: list[str] = field(default_factory=list)
    technical_interview: list[str] = field(default_factory=list)
    system_design: list[str] = field(default_factory=list)
    behavioral_interview: list[str] = field(default_factory=list)
    leadership_interview: list[str] = field(default_factory=list)
    coding_interview: list[str] = field(default_factory=list)
    evaluation_rubric: list[str] = field(default_factory=list)
    decision_checkpoints: list[str] = field(default_factory=list)
    post_interview_recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the interview strategy."""
        return asdict(self)


@dataclass
class ExecutiveActionPlan:
    """The executive action plan (Module 8): decision + onboarding roadmap."""

    primary_action: str
    rationale: str = ""
    alternatives: list[str] = field(default_factory=list)
    onboarding_plan: list[str] = field(default_factory=list)
    plan_30_day: list[str] = field(default_factory=list)
    plan_60_day: list[str] = field(default_factory=list)
    plan_90_day: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the action plan."""
        return asdict(self)


@dataclass
class ProvenanceEntry:
    """One evidence→claim link separating Evidence, Inference and Recommendation.

    Module 16 mandates that every statement reference a source and that the three
    epistemic kinds never blur. This record makes the separation auditable.
    """

    kind: str  # "Evidence" | "Inference" | "Recommendation"
    statement: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the provenance entry."""
        return asdict(self)


@dataclass
class ExecutiveHiringReport:
    """The unified executive hiring report (Module 1).

    Aggregates every structured intelligence output TalentMind already produced —
    resume, JD, committee, candidate intelligence, timeline, risk, interview,
    recommendation and pipeline — into one boardroom-ready artefact. It stores the
    upstream outputs verbatim (as dicts) and adds only presentation-layer
    synthesis; it never recomputes or alters an engine (Module 15 / 16).
    """

    report_id: str
    candidate_id: str
    template: str
    audience: str
    generated_on: str
    candidate_overview: dict[str, Any]
    narrative: ExecutiveNarrative
    resume_summary: str
    jd_summary: str
    role_intelligence: dict[str, Any]
    candidate_intelligence: dict[str, Any]
    committee: dict[str, Any]
    risk_dashboard: dict[str, Any]
    interview_strategy: InterviewStrategy
    action_plan: ExecutiveActionPlan
    business_intelligence: BusinessIntelligence
    charts: dict[str, Any]
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "report_id": self.report_id,
            "candidate_id": self.candidate_id,
            "template": self.template,
            "audience": self.audience,
            "generated_on": self.generated_on,
            "candidate_overview": self.candidate_overview,
            "narrative": self.narrative.to_dict(),
            "resume_summary": self.resume_summary,
            "jd_summary": self.jd_summary,
            "role_intelligence": self.role_intelligence,
            "candidate_intelligence": self.candidate_intelligence,
            "committee": self.committee,
            "risk_dashboard": self.risk_dashboard,
            "interview_strategy": self.interview_strategy.to_dict(),
            "action_plan": self.action_plan.to_dict(),
            "business_intelligence": self.business_intelligence.to_dict(),
            "charts": self.charts,
            "provenance": [p.to_dict() for p in self.provenance],
            "evidence_sources": list(self.evidence_sources),
            "warnings": list(self.warnings),
        }
