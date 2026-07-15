"""Structured schemas for the HiringAuditAgent (Phase 5 / Milestone 4).

The **Enterprise Hiring Audit & Explainability Platform** reconstructs the
complete hiring journey: why the decision was made, which AI agents participated,
which evidence influenced it, which assumptions were made, which human approvals
occurred, and whether executives can reconstruct the whole journey. It is **not** a
logging system, **not** an observability tool and **not** a legal-opinion engine
(Module 14): it never fabricates evidence, approvals, history, agent participation
or human actions, and it never rewrites history.

Two families live here:

* :class:`AuditNarrative` — the single validated :class:`BaseAIResponse` the AI
  Platform agent produces. **Score-free at the top level**.
* Dataclasses (:class:`DecisionTraceStep`, :class:`ProvenanceRecord`,
  :class:`EvidenceNode`, :class:`EvidenceEdge`, :class:`EvidenceGraph`,
  :class:`ReasoningExplanation`, :class:`TimelineEvent`,
  :class:`DecisionResponsibility`, :class:`GovernanceExplanation`,
  :class:`AuditReadiness`, :class:`HistoricalReconstruction`,
  :class:`HiringAuditReport`) — the assembled audit artefact.

Every element carries an epistemic register: Observed, Unavailable, Inferred,
Recommendation or Human Review (Module 14).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from pydantic import Field, field_validator

from src.ai.schemas.base import BaseAIResponse

REGISTERS = ("Observed", "Unavailable", "Inferred", "Recommendation", "Human Review")


# ---------------------------------------------------------------------------
# AI Platform output (BaseAIResponse — score-free top level)
# ---------------------------------------------------------------------------


class AuditNarrative(BaseAIResponse):
    """The hiring-audit / explainability narrative the agent produces (Modules 1, 3, 9).

    Score-free at the top level; every element is qualitative prose. It
    reconstructs and explains the journey — it never fabricates history or issues a
    legal opinion (Module 14).
    """

    executive_summary: str
    decision_journey_note: str = ""
    evidence_note: str = ""
    responsibility_note: str = ""
    governance_note: str = ""
    readiness_note: str = ""
    data_availability_note: str = ""
    key_findings: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    audit_recommendations: List[str] = Field(default_factory=list)
    outstanding_risks: List[str] = Field(default_factory=list)
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
# Module 1 — Decision trace
# ---------------------------------------------------------------------------


@dataclass
class DecisionTraceStep:
    """One chronological step in the reconstructed decision trace (Module 1)."""

    order: int
    stage: str
    origin_agent: str
    status: str = "Unavailable"  # Observed | Unavailable
    summary: str = ""
    evidence_source: str = ""
    register: str = "Unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 2 — Evidence provenance
# ---------------------------------------------------------------------------


@dataclass
class ProvenanceRecord:
    """Provenance for one piece of evidence (Module 2). Never fabricated."""

    evidence_source: str
    evidence_type: str
    origin_agent: str
    confidence: str = "Unknown"  # qualitative label or "Unknown"
    supporting_modules: List[str] = field(default_factory=list)
    register: str = "Observed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Evidence graph
# ---------------------------------------------------------------------------


@dataclass
class EvidenceNode:
    """A node in the evidence graph (an agent/engine or the final decision)."""

    id: str
    label: str
    kind: str = "agent"  # agent | decision
    present: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceEdge:
    """A directed edge: ``source`` evidence fed ``target`` decision."""

    source: str
    target: str
    active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceGraph:
    """The evidence graph (Modules 2, 10)."""

    nodes: List[EvidenceNode] = field(default_factory=list)
    edges: List[EvidenceEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": [n.to_dict() for n in self.nodes], "edges": [e.to_dict() for e in self.edges]}


# ---------------------------------------------------------------------------
# Module 3 — Reasoning explainability
# ---------------------------------------------------------------------------


@dataclass
class ReasoningExplanation:
    """Reasoning explainability, register by register (Module 3)."""

    observed_facts: List[str] = field(default_factory=list)
    derived_insights: List[str] = field(default_factory=list)
    business_reasoning: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    human_decisions: List[str] = field(default_factory=list)
    ai_decisions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 4 — Timeline
# ---------------------------------------------------------------------------


@dataclass
class TimelineEvent:
    """One event in the reconstructed hiring timeline (Module 4)."""

    order: int
    name: str
    actor: str = "System"  # AI | Human | System
    status: str = "Unavailable"  # Observed | Unavailable
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 5 — Human vs AI responsibility
# ---------------------------------------------------------------------------


@dataclass
class DecisionResponsibility:
    """One decision point attributed to AI or a specific human (Module 5)."""

    decision: str
    kind: str  # AI recommendation | Human override | Executive approval | Committee vote | Recruiter action | Hiring Manager action
    responsible_party: str  # "AI" | a human role
    status: str = "Observed"  # Observed | Unverified | Unavailable
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 6 — Governance explainability
# ---------------------------------------------------------------------------


@dataclass
class GovernanceExplanation:
    """One transparent governance explanation (Module 6)."""

    topic: str
    question: str
    explanation: str
    register: str = "Inferred"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 7 — Audit readiness
# ---------------------------------------------------------------------------


@dataclass
class AuditReadiness:
    """Audit readiness (Module 7)."""

    status: str = "Requires Review"  # Ready | Partially Ready | Not Ready | Requires Review
    readiness_level: str = "Medium"  # High | Medium | Low
    governance_completeness: str = ""
    missing_evidence: List[str] = field(default_factory=list)
    missing_documents: List[str] = field(default_factory=list)
    missing_approvals: List[str] = field(default_factory=list)
    unverified_decisions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Module 8 — Historical reconstruction
# ---------------------------------------------------------------------------


@dataclass
class HistoricalReconstruction:
    """Historical decision reconstruction (Module 8). Uses stored artifacts only."""

    available: bool = False
    status_message: str = "No historical audit archive connected; showing the current decision only."
    records: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Assembled report artefact (Module 9)
# ---------------------------------------------------------------------------


@dataclass
class HiringAuditReport:
    """The unified hiring-audit report (Modules 1-10).

    Reconstructs the decision trace, evidence provenance, evidence graph, reasoning
    explainability, timeline, human-vs-AI responsibility matrix, governance
    explanations, audit readiness and historical reconstruction — every one derived
    from existing artefacts. It never fabricates evidence/approvals/history and
    never rewrites history (Modules 13 / 14).
    """

    report_id: str
    candidate_id: str
    generated_on: str
    data_available: bool
    candidate_overview: Dict[str, Any]
    narrative: AuditNarrative
    decision_trace: List[DecisionTraceStep]
    provenance: List[ProvenanceRecord]
    evidence_graph: EvidenceGraph
    reasoning: ReasoningExplanation
    timeline: List[TimelineEvent]
    responsibility: List[DecisionResponsibility]
    governance_explanations: List[GovernanceExplanation]
    audit_readiness: AuditReadiness
    history: HistoricalReconstruction
    charts: Dict[str, Any] = field(default_factory=dict)
    evidence_sources: List[str] = field(default_factory=list)
    agents_participated: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the whole report."""
        return {
            "report_id": self.report_id,
            "candidate_id": self.candidate_id,
            "generated_on": self.generated_on,
            "data_available": self.data_available,
            "candidate_overview": self.candidate_overview,
            "narrative": self.narrative.to_dict(),
            "decision_trace": [s.to_dict() for s in self.decision_trace],
            "provenance": [p.to_dict() for p in self.provenance],
            "evidence_graph": self.evidence_graph.to_dict(),
            "reasoning": self.reasoning.to_dict(),
            "timeline": [t.to_dict() for t in self.timeline],
            "responsibility": [r.to_dict() for r in self.responsibility],
            "governance_explanations": [g.to_dict() for g in self.governance_explanations],
            "audit_readiness": self.audit_readiness.to_dict(),
            "history": self.history.to_dict(),
            "charts": self.charts,
            "evidence_sources": list(self.evidence_sources),
            "agents_participated": list(self.agents_participated),
            "warnings": list(self.warnings),
        }
