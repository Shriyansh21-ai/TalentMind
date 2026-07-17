"""Structured schemas for the InterviewStudioAgent (Phase 4 / Milestone 5).

The **Enterprise AI Interview Studio** transforms every structured intelligence
artefact TalentMind already produces (resume, JD, committee, candidate
intelligence, timeline, risk, recommendation and the deterministic interview
plan) into a complete, recruiter-ready interview package: an interview strategy,
an adaptive question flow, evaluation rubrics, interviewer guides, feedback
templates and a decision matrix. It creates **no new hiring logic and no new
ranking** — it consumes existing outputs and restates them for the interview
panel (Module 16 Safety).

Two families live here:

* :class:`InterviewStudioNarrative` — the single validated
  :class:`BaseAIResponse` the AI Platform agent produces. It is **score-free at
  the top level** (the platform safety guard rejects
  ``score``/``rating``/``percent``/``confidence_value`` fields), so every element
  is a qualitative label or evidence-anchored prose.
* Dataclasses (:class:`InterviewStrategy`, :class:`InterviewQuestion`,
  :class:`RiskValidation`, :class:`InterviewStage`, :class:`RubricDimension`,
  :class:`DecisionBand`, :class:`DecisionMatrix`, :class:`FeedbackForms`,
  :class:`LiveInterviewAssistant`, :class:`ProvenanceEntry`,
  :class:`InterviewStudioReport`) — the assembled interview package the engine
  produces for the UI / copilot / export layer. This mirrors the executive
  report's ``ExecutiveHiringReport`` pattern.

The schema is deliberately composable so Module 14 extensions (Voice Interview,
AI Interviewer, Coding Sandbox, Live Pair Programming, Video/Emotion Analysis,
Meeting Transcript) can consume or extend it without a redesign.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class InterviewStudioNarrative(BaseAIResponse):
    """The interview-strategy narrative the agent produces (Modules 1, 2).

    Score-free at the top level; ``readiness_label`` is a qualitative label,
    never a number. Every element restates the structured evidence — it invents
    no candidate experience, no interview result and no recommendation
    (Module 16).
    """

    interview_summary: str
    strategy_overview: str = ""
    recommended_focus: str = ""
    personalization_note: str = ""
    coverage_note: str = ""
    risk_validation_note: str = ""
    readiness_label: str = "Ready to Interview"
    key_probes: list[str] = Field(default_factory=list)
    watch_areas: list[str] = Field(default_factory=list)
    confidence_note: str = ""

    @field_validator("interview_summary")
    @classmethod
    def _summary_non_empty(cls, value: str) -> str:
        """Ensure the interview summary is a non-empty string."""
        text = (value or "").strip()
        if not text:
            raise ValueError("interview_summary must not be empty")
        return text


# ---------------------------------------------------------------------------
# Assembled package artefacts (dataclasses — engine output for UI / export)
# ---------------------------------------------------------------------------


@dataclass
class InterviewStrategy:
    """The interview strategy (Module 1): depth, length, stages, difficulty.

    Every field is derived deterministically from the seniority, role fit and
    evidence coverage already computed by the engines — never invented.
    """

    depth: str = "standard"
    length_minutes: int = 240
    stage_count: int = 5
    difficulty: str = "Calibrated"
    objectives: list[str] = field(default_factory=list)
    priorities: list[str] = field(default_factory=list)
    decision_checkpoints: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the strategy."""
        return asdict(self)


@dataclass
class InterviewQuestion:
    """A single interview question traced back to existing intelligence.

    Module 16 mandates that every question separate Evidence, the Question, the
    Evaluation Signal and the Recommendation, and that every question trace to a
    source. ``source`` records that provenance.
    """

    text: str
    competency: str = ""
    category: str = (
        "technical"  # technical | system_design | coding | behavioral | leadership | role
    )
    difficulty: str = "Core"  # Warm-up | Core | Deep | Stretch
    expected_answer: str = ""
    evaluation_criteria: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    source: str = "TalentMind synthesis"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the question."""
        return asdict(self)


@dataclass
class RiskValidation:
    """A risk converted into an interview validation question (Module 6).

    Encodes the mandated chain: Risk -> Validation Question -> Expected Evidence
    -> Pass Criteria. Every entry is sourced from the Risk engine, the committee
    or the recommendation engine — never invented.
    """

    risk: str
    category: str = "resume"  # resume | timeline | committee | recommendation
    validation_question: str = ""
    expected_evidence: str = ""
    pass_criteria: str = ""
    source: str = "Resume Risk Detection"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the risk validation."""
        return asdict(self)


@dataclass
class InterviewStage:
    """One stage in the adaptive interview roadmap (Module 2)."""

    name: str
    objective: str = ""
    duration_minutes: int = 45
    interviewer: str = ""
    focus: list[str] = field(default_factory=list)
    checkpoint: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the stage."""
        return asdict(self)


@dataclass
class RubricDimension:
    """One scoring dimension in the evaluation rubric (Module 7).

    ``levels`` maps a qualitative band (Strong / Solid / Mixed / Weak) to a
    behavioral descriptor, giving interviewers a shared, evidence-anchored bar.
    """

    name: str
    description: str = ""
    weight: str = "Standard"  # qualitative weight label (never a number at top level)
    levels: dict[str, str] = field(default_factory=dict)
    evidence_to_look_for: list[str] = field(default_factory=list)
    source: str = "Interview Intelligence"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the rubric dimension."""
        return asdict(self)


@dataclass
class DecisionBand:
    """One band of the decision matrix (Module 8)."""

    label: str  # Strong Hire | Hire | Hold | Reject
    signals: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    confidence_label: str = "Moderate"
    escalation: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the decision band."""
        return asdict(self)


@dataclass
class DecisionMatrix:
    """The interview decision matrix (Module 8).

    Maps interview outcomes to Strong Hire / Hire / Hold / Reject with the
    signals, evidence and confidence each rests on, plus escalation criteria and
    an explicit note on how it aligns with the AI Hiring Committee.
    """

    bands: list[DecisionBand] = field(default_factory=list)
    escalation_criteria: list[str] = field(default_factory=list)
    committee_alignment: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the decision matrix."""
        return {
            "bands": [b.to_dict() for b in self.bands],
            "escalation_criteria": list(self.escalation_criteria),
            "committee_alignment": self.committee_alignment,
        }


@dataclass
class FeedbackForms:
    """Structured feedback templates (Module 10).

    Every form is a list of prompts/fields the interviewer or manager fills in —
    the studio never invents interview results, it only supplies the structure.
    """

    interviewer_form: list[str] = field(default_factory=list)
    hiring_manager_form: list[str] = field(default_factory=list)
    panel_form: list[str] = field(default_factory=list)
    candidate_summary_template: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the feedback forms."""
        return asdict(self)


@dataclass
class LiveInterviewAssistant:
    """Real-time interviewer support (Module 9).

    Structured hooks only — no voice/AI-interviewer features yet, but the shape
    is stable so Module 14 can extend it without a redesign.
    """

    interviewer_notes_template: list[str] = field(default_factory=list)
    question_checklist: list[str] = field(default_factory=list)
    evaluation_checklist: list[str] = field(default_factory=list)
    risk_reminders: list[str] = field(default_factory=list)
    followup_suggestions: list[str] = field(default_factory=list)
    timer_hooks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the live assistant."""
        return asdict(self)


@dataclass
class ProvenanceEntry:
    """One evidence->claim link separating Evidence, Inference and Recommendation.

    Module 16 mandates that every element reference a source and that the
    epistemic kinds never blur. This record makes the separation auditable.
    """

    kind: str  # "Evidence" | "Inference" | "Recommendation"
    statement: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the provenance entry."""
        return asdict(self)


@dataclass
class InterviewStudioReport:
    """The unified interview package (Modules 1-12).

    Aggregates the interview strategy, adaptive roadmap, technical / behavioral /
    role-specific questions, risk-validation questions, evaluation rubrics,
    decision matrix, feedback templates and live-assistant hooks — every one
    derived from existing structured intelligence. It stores the upstream signals
    verbatim and adds only interview-preparation synthesis; it never recomputes
    or alters an engine (Modules 15 / 16).
    """

    plan_id: str
    candidate_id: str
    role: str
    role_name: str
    depth: str
    generated_on: str
    candidate_overview: dict[str, Any]
    narrative: InterviewStudioNarrative
    strategy: InterviewStrategy
    roadmap: list[InterviewStage]
    technical_questions: list[InterviewQuestion]
    behavioral_questions: list[InterviewQuestion]
    role_specific_questions: list[InterviewQuestion]
    risk_validations: list[RiskValidation]
    rubrics: list[RubricDimension]
    decision_matrix: DecisionMatrix
    feedback_forms: FeedbackForms
    live_assistant: LiveInterviewAssistant
    charts: dict[str, Any] = field(default_factory=dict)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def all_questions(self) -> list[InterviewQuestion]:
        """Return every generated question across all sections."""
        return [
            *self.technical_questions,
            *self.behavioral_questions,
            *self.role_specific_questions,
        ]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict of the whole package."""
        return {
            "plan_id": self.plan_id,
            "candidate_id": self.candidate_id,
            "role": self.role,
            "role_name": self.role_name,
            "depth": self.depth,
            "generated_on": self.generated_on,
            "candidate_overview": self.candidate_overview,
            "narrative": self.narrative.to_dict(),
            "strategy": self.strategy.to_dict(),
            "roadmap": [s.to_dict() for s in self.roadmap],
            "technical_questions": [q.to_dict() for q in self.technical_questions],
            "behavioral_questions": [q.to_dict() for q in self.behavioral_questions],
            "role_specific_questions": [q.to_dict() for q in self.role_specific_questions],
            "risk_validations": [r.to_dict() for r in self.risk_validations],
            "rubrics": [r.to_dict() for r in self.rubrics],
            "decision_matrix": self.decision_matrix.to_dict(),
            "feedback_forms": self.feedback_forms.to_dict(),
            "live_assistant": self.live_assistant.to_dict(),
            "charts": self.charts,
            "provenance": [p.to_dict() for p in self.provenance],
            "evidence_sources": list(self.evidence_sources),
            "warnings": list(self.warnings),
        }
