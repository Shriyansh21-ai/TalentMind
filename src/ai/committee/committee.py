"""HiringCommitteeEngine — the committee lifecycle orchestrator (Modules 1-9, 15).

Ties the panel, moderator, consensus, conflict resolution, confidence metrics,
executive chair and memory into one committee meeting. It **only consumes**
existing structured outputs (resume/JD analyses + the candidate insight bundle)
— it never re-runs or modifies a deterministic engine, and every underlying
analysis is cached, so the committee never recomputes (Module 15).

Lifecycle::

    gather evidence (cached) → independent reviews (parallel, workflow engine)
    → discussion → evidence-weighted consensus → conflict resolution
    → confidence metrics → executive chair decision (AI Platform) → memory
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.ai.committee.chair import ChairInput, committee_chair_agent, compose_committee_decision
from src.ai.committee.conflict_resolution import detect_conflicts
from src.ai.committee.consensus import build_consensus
from src.ai.committee.executive_report import (
    build_committee_report,
    compute_confidence_metrics,
)
from src.ai.committee.members import build_panel
from src.ai.committee.memory import CommitteeMemory
from src.ai.committee.moderator import CommitteeModerator
from src.ai.committee.schemas import (
    CommitteeDecision,
    CommitteeMode,
    CommitteeReport,
)
from src.ai.core.runner import AgentRunner


@dataclass
class EvidenceBundle:
    """All structured evidence one committee meeting consumes (never recomputed).

    Every field is an existing engine/agent output, gathered once and passed to
    the members. The committee reasons only over this bundle.
    """

    candidate: Any
    candidate_id: str
    title: str = ""
    company: str = ""
    years_of_experience: float = 0.0
    location: str = ""
    resume_analysis: Any = None  # ResumeAnalysis | None
    jd_analysis: Any = None  # JDAnalysis | None
    intelligence: Any = None  # CandidateIntelligence | None
    timeline: Any = None  # CareerTimelineAnalysis | None
    risk: Any = None  # RiskReport | None
    recommendation: Any = None  # HiringRecommendation | None
    interview_plan: Any = None  # InterviewPlan | None
    gap: dict = field(default_factory=dict)
    available_sources: list[str] = field(default_factory=list)


InsightsFn = Callable[[Any, str], Any]


def gather_evidence(
    candidate: Any,
    jd: str = "",
    *,
    insights_fn: InsightsFn | None = None,
    ai_runner: AgentRunner | None = None,
) -> EvidenceBundle:
    """Gather every structured output the committee needs (all cached upstream)."""
    from src.ai.agents.jd.agent import JDAnalystInput, jd_analyst_agent
    from src.ai.agents.resume.agent import ResumeAnalystInput, resume_analyst_agent
    from src.interview.planner import build_interview_plan

    runner = ai_runner or AgentRunner()

    if insights_fn is None:
        from src.insights.builder import build_insights

        insights_fn = build_insights
    insights = insights_fn(candidate, jd)

    interview_plan = None
    try:
        interview_plan = build_interview_plan(insights)
    except Exception:  # interview plan is optional evidence
        interview_plan = None

    resume_analysis = None
    try:
        r = runner.run(
            resume_analyst_agent,
            ResumeAnalystInput(candidate_id=candidate.candidate_id, candidate=candidate, jd=jd),
        )
        resume_analysis = r.data if r.ok else None
    except Exception:
        resume_analysis = None

    jd_analysis = None
    if jd and jd.strip():
        try:
            j = runner.run(jd_analyst_agent, JDAnalystInput(jd_text=jd))
            jd_analysis = j.data if j.ok else None
        except Exception:
            jd_analysis = None

    profile = candidate.profile
    bundle = EvidenceBundle(
        candidate=candidate,
        candidate_id=candidate.candidate_id,
        title=profile.current_title,
        company=profile.current_company,
        years_of_experience=profile.years_of_experience,
        location=profile.location,
        resume_analysis=resume_analysis,
        jd_analysis=jd_analysis,
        intelligence=getattr(insights, "intelligence", None),
        timeline=getattr(insights, "timeline", None),
        risk=getattr(insights, "risk", None),
        recommendation=getattr(insights, "recommendation", None),
        interview_plan=interview_plan,
        gap=getattr(insights, "gap", {}) or {},
    )
    bundle.available_sources = _sources(bundle)
    return bundle


def _sources(bundle: EvidenceBundle) -> list[str]:
    """Return the labels of the evidence sources actually present."""
    mapping = [
        (bundle.resume_analysis, "Resume Analyst Agent"),
        (bundle.jd_analysis, "JD Analyst Agent"),
        (bundle.intelligence, "Candidate Intelligence engine"),
        (bundle.risk, "Risk Intelligence"),
        (bundle.timeline, "Career Timeline Intelligence"),
        (bundle.interview_plan, "Interview Intelligence"),
        (bundle.recommendation, "Hiring Recommendation engine"),
    ]
    return [label for value, label in mapping if value is not None]


class HiringCommitteeEngine:
    """Runs a full AI Hiring Committee meeting and returns a report."""

    _counter = 0

    def __init__(
        self,
        *,
        repository: Any = None,
        insights_fn: InsightsFn | None = None,
        ai_runner: AgentRunner | None = None,
        moderator: CommitteeModerator | None = None,
        memory: CommitteeMemory | None = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.repository = repository
        self.insights_fn = insights_fn
        self.ai_runner = ai_runner or AgentRunner()
        self.moderator = moderator or CommitteeModerator()
        self.memory = memory or CommitteeMemory()
        self.panel = build_panel()

    def run(
        self,
        candidate: Any = None,
        *,
        candidate_id: str | None = None,
        jd: str = "",
        mode: CommitteeMode = CommitteeMode.BALANCED,
    ) -> CommitteeReport:
        """Convene the committee for a candidate and return the executive report."""
        if candidate is None:
            if self.repository is None or candidate_id is None:
                raise ValueError("Provide a candidate, or a repository + candidate_id.")
            candidate = self.repository.get(candidate_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate {candidate_id!r}.")

        if isinstance(mode, str):
            mode = CommitteeMode(mode)

        bundle = gather_evidence(
            candidate, jd, insights_fn=self.insights_fn, ai_runner=self.ai_runner
        )

        # 1) Independent reviews (parallel, via the orchestration workflow engine).
        opinions = self.moderator.collect_independent_reviews(self.panel, bundle, mode)
        # 2) Discussion round.
        discussion = self.moderator.discuss(opinions)
        # 3) Evidence-weighted consensus.
        consensus = build_consensus(opinions, mode)
        # 4) Conflict resolution.
        conflicts = detect_conflicts(opinions)
        # 5) Confidence metrics.
        confidence = compute_confidence_metrics(opinions, consensus, bundle)

        # 6) Executive chair decision (AI Platform).
        chair_input = ChairInput(
            candidate_overview={
                "candidate_id": bundle.candidate_id,
                "title": bundle.title,
                "company": bundle.company,
                "years_of_experience": bundle.years_of_experience,
                "location": bundle.location,
            },
            resume_summary=bundle.resume_analysis.executive_summary
            if bundle.resume_analysis
            else "",
            jd_summary=bundle.jd_analysis.executive_summary if bundle.jd_analysis else "",
            mode=mode.value,
            opinions=[o.to_dict() for o in opinions],
            consensus=consensus.to_dict(),
            conflicts=[c.to_dict() for c in conflicts],
            confidence=confidence.to_dict(),
            discussion=discussion.to_dict(),
        )
        decision = self._chair_decision(chair_input)

        warnings: list[str] = []
        if not bundle.jd_analysis:
            warnings.append("No JD provided — role-fit reasoning is limited.")
        if len(bundle.available_sources) < 5:
            warnings.append("Fewer than 5 evidence sources; confidence is reduced.")

        report = build_committee_report(
            meeting_id=self._next_meeting_id(bundle.candidate_id, mode),
            bundle=bundle,
            mode=mode.value,
            opinions=opinions,
            discussion=discussion,
            consensus=consensus,
            conflicts=conflicts,
            confidence=confidence,
            decision=decision,
            warnings=warnings,
        )
        self.memory.remember_meeting(report.meeting_id, report.to_dict())
        return report

    # -- internals ----------------------------------------------------------

    def _chair_decision(self, chair_input: ChairInput) -> CommitteeDecision:
        """Run the chair agent; fall back to the deterministic composer on failure."""
        try:
            result = self.ai_runner.run(committee_chair_agent, chair_input)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return CommitteeDecision(**compose_committee_decision(chair_input.as_evidence()))

    @classmethod
    def _next_meeting_id(cls, candidate_id: str, mode: CommitteeMode) -> str:
        """Return a process-unique meeting id."""
        cls._counter += 1
        return f"committee_{candidate_id}_{mode.value}_{cls._counter}"


# ---------------------------------------------------------------------------
# Orchestration registration (Module: register with the orchestration platform)
# ---------------------------------------------------------------------------


def _register_with_orchestration() -> None:
    """Register the committee as a ``hiring_committee`` orchestration capability."""
    try:
        from src.ai.orchestration.adapters import FunctionAgent
        from src.ai.orchestration.context.context import SharedContext
        from src.ai.orchestration.models import AgentOutput, Task
        from src.ai.orchestration.registry.agent_registry import (
            AgentDescriptor,
            orchestration_registry,
        )

        def _run(task: Task, context: SharedContext) -> AgentOutput:
            payload = task.payload or {}
            candidate = payload.get("candidate") or getattr(context, "candidate", None)
            jd = payload.get("jd") or getattr(context, "jd", "")
            if candidate is None:
                return AgentOutput(
                    task_id=task.id,
                    agent="hiring_committee",
                    ok=False,
                    error="Hiring committee needs a candidate in the task payload or context.",
                )
            mode = payload.get("mode", CommitteeMode.BALANCED)
            report = HiringCommitteeEngine().run(candidate=candidate, jd=jd, mode=mode)
            return AgentOutput(
                task_id=task.id,
                agent="hiring_committee",
                ok=True,
                data=report.to_dict(),
                summary=(
                    f"Committee → {report.consensus.recommendation.value} "
                    f"({report.consensus.level.value})."
                ),
                evidence_sources=report.evidence_sources,
            )

        descriptor = AgentDescriptor(
            name="hiring_committee",
            capabilities=["hiring_committee", "committee_decision"],
            description="AI Hiring Committee — multi-agent decision engine.",
            tags=["committee", "decision", "flagship"],
        )
        orchestration_registry.register(FunctionAgent(descriptor, _run))
    except Exception:  # orchestration optional; never block committee import
        pass


# A shared default engine + orchestration registration on import.
hiring_committee_engine = HiringCommitteeEngine()
_register_with_orchestration()
