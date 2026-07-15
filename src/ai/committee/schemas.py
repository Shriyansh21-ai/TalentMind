"""Committee vocabulary + structured outputs (Modules 4, 6, 9, 13).

Internal deliberation structures are dataclasses (opinions, consensus, conflicts,
discussion, confidence). The Executive Chair's AI output is the single
:class:`BaseAIResponse` — :class:`CommitteeDecision` — which is score-free at the
top level (the platform safety guard rejects score-like top-level fields). The
assembled :class:`CommitteeReport` is the engine's final artefact for the UI /
copilot / export.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Recommendation(str, Enum):
    """A committee stance on hiring (member- or committee-level)."""

    STRONG_HIRE = "Strong Hire"
    HIRE = "Hire"
    LEAN_HIRE = "Lean Hire"
    HOLD = "Hold"
    LEAN_NO_HIRE = "Lean No Hire"
    NO_HIRE = "No Hire"


class ConsensusLevel(str, Enum):
    """How aligned the committee is (Module 4)."""

    STRONG = "Strong Consensus"
    MODERATE = "Moderate Consensus"
    SPLIT = "Split Decision"
    NONE = "No Consensus"


class CommitteeMode(str, Enum):
    """Deterministic committee operating modes (Module 12)."""

    BALANCED = "balanced"
    OPTIMISTIC = "optimistic"
    CONSERVATIVE = "conservative"


# ---------------------------------------------------------------------------
# Internal deliberation structures (dataclasses)
# ---------------------------------------------------------------------------


@dataclass
class MemberOpinion:
    """One committee member's independent review (Module 2)."""

    role: str
    role_title: str
    recommendation: Recommendation
    confidence: float
    opinion: str
    strengths: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    abstained: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the opinion."""
        data = asdict(self)
        data["recommendation"] = self.recommendation.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemberOpinion":
        """Rehydrate a :class:`MemberOpinion` from its dict form."""
        data = dict(data)
        data["recommendation"] = Recommendation(data["recommendation"])
        return cls(**data)


@dataclass
class Consensus:
    """The evidence-weighted consensus result (Module 4)."""

    level: ConsensusLevel
    recommendation: Recommendation
    weighted_stance: float
    agreement_ratio: float
    reasoning: str = ""
    stance_distribution: Dict[str, int] = field(default_factory=dict)
    member_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the consensus."""
        return {
            "level": self.level.value,
            "recommendation": self.recommendation.value,
            "weighted_stance": round(self.weighted_stance, 3),
            "agreement_ratio": round(self.agreement_ratio, 3),
            "reasoning": self.reasoning,
            "stance_distribution": self.stance_distribution,
            "member_weights": {k: round(v, 3) for k, v in self.member_weights.items()},
        }


@dataclass
class Conflict:
    """A resolved disagreement between two members (Module 5)."""

    member_a: str
    member_b: str
    stance_gap: float
    root_cause: str
    missing_evidence: str
    assumption_difference: str
    confidence_difference: str
    resolution_strategy: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the conflict."""
        return asdict(self)


@dataclass
class DiscussionRound:
    """The output of the discussion phase (Module 3)."""

    agreements: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)
    challenges: List[Dict[str, Any]] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the discussion round."""
        return asdict(self)


@dataclass
class ConfidenceMetrics:
    """Explainable hiring-confidence metrics (Module 13). 0-100 each."""

    evidence_coverage: float
    consensus_strength: float
    confidence_distribution: float
    unknown_risk: float
    decision_stability: float
    overall: float
    explanations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the confidence metrics."""
        data = asdict(self)
        for key in ("evidence_coverage", "consensus_strength", "confidence_distribution", "unknown_risk", "decision_stability", "overall"):
            data[key] = round(getattr(self, key), 1)
        return data


# ---------------------------------------------------------------------------
# Executive Chair AI output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class CommitteeDecision(BaseAIResponse):
    """The Executive Chair's structured decision (Module 6).

    Score-free at the top level; ``recommendation`` is a label (e.g. "Hire"), not
    a number. Every element is grounded in the committee's structured deliberation.
    """

    executive_summary: str
    recommendation: str = "Hold"
    business_justification: str = ""
    technical_justification: str = ""
    hiring_risks: List[str] = Field(default_factory=list)
    interview_priorities: List[str] = Field(default_factory=list)
    remaining_unknowns: List[str] = Field(default_factory=list)
    follow_up_actions: List[str] = Field(default_factory=list)
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
# Assembled committee report (engine output for UI / copilot / export)
# ---------------------------------------------------------------------------


@dataclass
class CommitteeReport:
    """The full executive hiring report the committee produces (Module 9)."""

    meeting_id: str
    candidate_id: str
    mode: str
    candidate_overview: Dict[str, Any]
    resume_summary: str
    jd_summary: str
    opinions: List[MemberOpinion]
    discussion: DiscussionRound
    consensus: Consensus
    conflicts: List[Conflict]
    confidence: ConfidenceMetrics
    decision: CommitteeDecision
    evidence_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "meeting_id": self.meeting_id,
            "candidate_id": self.candidate_id,
            "mode": self.mode,
            "candidate_overview": self.candidate_overview,
            "resume_summary": self.resume_summary,
            "jd_summary": self.jd_summary,
            "opinions": [o.to_dict() for o in self.opinions],
            "discussion": self.discussion.to_dict(),
            "consensus": self.consensus.to_dict(),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "confidence": self.confidence.to_dict(),
            "decision": self.decision.to_dict(),
            "evidence_sources": self.evidence_sources,
            "warnings": self.warnings,
        }
