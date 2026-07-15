"""InterviewStudioEngine — assembles the unified interview package (Module 11).

This is the Module 1/2 collector. It **consumes existing structured intelligence
only** — it reuses the committee's ``gather_evidence`` (cached resume/JD analyses
+ the candidate insight bundle + the deterministic interview plan), optionally
runs the Hiring Committee, runs the InterviewStudioAgent for the strategy
narrative, and assembles the strategy, adaptive roadmap, question sets, risk
validations, rubrics, decision matrix, feedback forms, live-assistant hooks and
charts into one :class:`InterviewStudioReport`. It never re-ranks, never
recomputes an engine, and never fabricates (Modules 15 / 16).

All collaborators are injected (AI runner, committee engine, insights function),
so the engine is fully testable and swappable — SOLID / DI by construction.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from src.ai.core.runner import AgentRunner

from src.ai.agents.interview_studio import charts as charts_mod
from src.ai.agents.interview_studio import decision_matrix as decision_mod
from src.ai.agents.interview_studio import evaluation as evaluation_mod
from src.ai.agents.interview_studio import feedback as feedback_mod
from src.ai.agents.interview_studio import planner as planner_mod
from src.ai.agents.interview_studio import question_generator as questions_mod
from src.ai.agents.interview_studio import rubrics as rubrics_mod
from src.ai.agents.interview_studio import strategy as strategy_mod
from src.ai.agents.interview_studio import validators
from src.ai.agents.interview_studio.agent import (
    InterviewStudioInput,
    build_interview_evidence,
    interview_studio_agent,
)
from src.ai.agents.interview_studio.composer import compose_interview_narrative
from src.ai.agents.interview_studio.schemas import (
    InterviewStudioNarrative,
    InterviewStudioReport,
)
from src.ai.agents.interview_studio.templates import RoleProfile, detect_role, get_role

from src.ai.committee.committee import HiringCommitteeEngine, gather_evidence
from src.ai.committee.schemas import CommitteeMode


class InterviewStudioEngine:
    """Builds a unified :class:`InterviewStudioReport` from existing intelligence."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: Optional[AgentRunner] = None,
        committee_engine: Optional[HiringCommitteeEngine] = None,
        insights_fn: Optional[Any] = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.committee_engine = committee_engine

    # -- public API ---------------------------------------------------------

    def build(
        self,
        candidate: Any = None,
        *,
        candidate_id: Optional[str] = None,
        repository: Any = None,
        jd: str = "",
        role: str = "",
        depth: str = "",
        mode: CommitteeMode = CommitteeMode.BALANCED,
        run_committee: bool = True,
        generated_on: str = "",
    ) -> InterviewStudioReport:
        """Collect all intelligence for a candidate and assemble the interview package."""
        if candidate is None:
            if repository is None or candidate_id is None:
                raise ValueError("Provide a candidate, or a repository + candidate_id.")
            candidate = repository.get(candidate_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate {candidate_id!r}.")
        if isinstance(mode, str):
            mode = CommitteeMode(mode)

        # 1) Gather existing structured outputs (all cached upstream — Module 15).
        bundle = gather_evidence(
            candidate, jd, insights_fn=self.insights_fn, ai_runner=self.ai_runner
        )

        # 2) Committee decision (reuses the same cached outputs).
        committee_dict: Dict[str, Any] = {}
        if run_committee:
            engine = self.committee_engine or HiringCommitteeEngine(
                insights_fn=self.insights_fn, ai_runner=self.ai_runner
            )
            try:
                committee_dict = engine.run(candidate=candidate, jd=jd, mode=mode).to_dict()
            except Exception:  # committee is optional evidence; degrade gracefully
                committee_dict = {}

        # 3) Normalize each source to a plain dict (no recomputation).
        overview = self._overview(bundle)
        resume = self._resume(bundle.resume_analysis)
        jd_norm = self._jd(bundle.jd_analysis)
        intelligence = self._model_dict(bundle.intelligence)
        timeline = self._model_dict(bundle.timeline)
        risk = self._model_dict(bundle.risk)
        recommendation = self._model_dict(bundle.recommendation)
        interview = self._model_dict(bundle.interview_plan)
        overview["career_story"] = timeline.get("career_story", "")

        # 4) Resolve the role path + depth (Module 5, personalized — never generic).
        role_profile = self._resolve_role(role, overview, bundle.jd_analysis, jd_norm)
        payload = InterviewStudioInput(
            candidate_id=bundle.candidate_id,
            role=role_profile.key,
            role_name=role_profile.name,
            depth=depth or strategy_mod.choose_depth(
                {"candidate_overview": overview, "intelligence": intelligence}, role_profile
            ),
            candidate_overview=overview,
            resume=resume,
            jd=jd_norm,
            committee=committee_dict,
            intelligence=intelligence,
            timeline=timeline,
            risk=risk,
            recommendation=recommendation,
            interview=interview,
        )
        evidence = build_interview_evidence(payload)

        # 5) Strategy narrative via the AI Platform agent (offline composer fallback).
        narrative = self._narrative(payload, evidence)

        # 6) Deterministic package layers (all derived from the evidence).
        strategy = strategy_mod.build_strategy(evidence, role_profile, payload.depth)
        roadmap = planner_mod.build_roadmap(evidence, strategy, role_profile)
        technical = questions_mod.technical_questions(evidence, role_profile)
        behavioral = questions_mod.behavioral_questions(evidence, role_profile)
        role_specific = questions_mod.role_specific_questions(evidence, role_profile)
        risk_validations = questions_mod.risk_validations(evidence)
        rubrics = rubrics_mod.build_rubrics(evidence, role_profile)
        matrix = decision_mod.build_decision_matrix(evidence)
        feedback_forms = feedback_mod.build_feedback_forms(rubrics, evidence)

        all_questions = [*technical, *behavioral, *role_specific]
        live_assistant = evaluation_mod.build_live_assistant(
            roadmap, all_questions, rubrics, risk_validations
        )
        chart_data = charts_mod.build_chart_data(
            evidence=evidence,
            strategy=strategy,
            stages=roadmap,
            questions=all_questions,
            rubrics=rubrics,
            risk_validations=risk_validations,
            decision_matrix=matrix,
        )

        # 7) Provenance + safety warnings (Module 16).
        provenance = validators.build_provenance(narrative, evidence, risk_validations)
        warnings = validators.validate_provenance(provenance)
        warnings += validators.evidence_coverage_warnings(evidence)

        return InterviewStudioReport(
            plan_id=self._next_plan_id(bundle.candidate_id),
            candidate_id=bundle.candidate_id,
            role=role_profile.key,
            role_name=role_profile.name,
            depth=payload.depth,
            generated_on=generated_on,
            candidate_overview=overview,
            narrative=narrative,
            strategy=strategy,
            roadmap=roadmap,
            technical_questions=technical,
            behavioral_questions=behavioral,
            role_specific_questions=role_specific,
            risk_validations=risk_validations,
            rubrics=rubrics,
            decision_matrix=matrix,
            feedback_forms=feedback_forms,
            live_assistant=live_assistant,
            charts=chart_data,
            provenance=provenance,
            evidence_sources=validators.available_sources(evidence),
            warnings=list(dict.fromkeys(warnings)),
        )

    # -- normalization helpers ---------------------------------------------

    @staticmethod
    def _overview(bundle: Any) -> Dict[str, Any]:
        return {
            "candidate_id": bundle.candidate_id,
            "title": bundle.title,
            "company": bundle.company,
            "years_of_experience": bundle.years_of_experience,
            "location": bundle.location,
        }

    @staticmethod
    def _model_dict(model: Any) -> Dict[str, Any]:
        """Return a plain dict for a pydantic model / dataclass / dict / None."""
        if model is None:
            return {}
        if hasattr(model, "model_dump"):
            return model.model_dump()
        if hasattr(model, "to_dict"):
            return model.to_dict()
        try:
            return asdict(model)
        except TypeError:
            return dict(model) if isinstance(model, dict) else {}

    def _resume(self, resume_analysis: Any) -> Dict[str, Any]:
        if resume_analysis is None:
            return {}
        quality = self._model_dict(getattr(resume_analysis, "resume_quality", None))
        return {
            "executive_summary": getattr(resume_analysis, "executive_summary", ""),
            "quality": quality,
            "strengths": list(getattr(resume_analysis, "strengths", []) or []),
            "weaknesses": list(getattr(resume_analysis, "weaknesses", []) or []),
        }

    def _jd(self, jd_analysis: Any) -> Dict[str, Any]:
        if jd_analysis is None:
            return {}
        role_intel = self._model_dict(getattr(jd_analysis, "role_intelligence", None))
        return {
            "executive_summary": getattr(jd_analysis, "executive_summary", ""),
            "quality": self._model_dict(getattr(jd_analysis, "quality", None)),
            "role_intelligence": role_intel,
        }

    @staticmethod
    def _resolve_role(role: str, overview: Dict[str, Any], jd_analysis: Any, jd_norm: Dict[str, Any]) -> RoleProfile:
        """Resolve the role path from an explicit key or infer it from title + JD."""
        if role:
            return get_role(role)
        # Infer from the candidate's title, the JD's inferred seniority/level and summary.
        hints: List[str] = [str(overview.get("title", ""))]
        role_intel = jd_norm.get("role_intelligence") or {}
        hints.append(str(role_intel.get("role_title", "")))
        hints.append(str(role_intel.get("seniority", "")))
        hints.append(str(jd_norm.get("executive_summary", "")))
        if jd_analysis is not None:
            hints.append(str(getattr(jd_analysis, "executive_summary", "")))
        return detect_role(*hints)

    # -- narrative ----------------------------------------------------------

    def _narrative(self, payload: InterviewStudioInput, evidence: Dict[str, Any]) -> InterviewStudioNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        try:
            result = self.ai_runner.run(interview_studio_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return InterviewStudioNarrative(**compose_interview_narrative(evidence))

    @classmethod
    def _next_plan_id(cls, candidate_id: str) -> str:
        """Return a process-unique plan id."""
        cls._counter += 1
        return f"interview_plan_{candidate_id}_{cls._counter}"


# A shared default engine for the tool / copilot / UI.
interview_studio_engine = InterviewStudioEngine()
