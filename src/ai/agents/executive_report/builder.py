"""ExecutiveReportBuilder — assembles the unified executive hiring report.

This is the Module 1 collector. It **consumes existing structured intelligence
only** — it reuses the committee's ``gather_evidence`` (cached resume/JD analyses
+ the candidate insight bundle) and the Hiring Committee engine, runs the
ExecutiveHiringReportAgent for the executive narrative, and assembles everything
into one :class:`ExecutiveHiringReport`. It never re-ranks, never recomputes an
engine, and never fabricates (Modules 15 / 16).

All collaborators are injected (AI runner, committee engine, insights function),
so the builder is fully testable and swappable — SOLID / DI by construction.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.ai.agents.executive_report import charts as charts_mod
from src.ai.agents.executive_report import validators
from src.ai.agents.executive_report.agent import (
    ExecutiveReportInput,
    build_executive_evidence,
    executive_report_agent,
)
from src.ai.agents.executive_report.composer import compose_executive_narrative
from src.ai.agents.executive_report.schemas import (
    BusinessIntelligence,
    Estimate,
    ExecutiveActionPlan,
    ExecutiveHiringReport,
    ExecutiveNarrative,
    InterviewStrategy,
)
from src.ai.committee.committee import HiringCommitteeEngine, gather_evidence
from src.ai.committee.schemas import CommitteeMode
from src.ai.core.runner import AgentRunner

# Map any upstream recommendation label -> an executive action disposition (M8).
_ACTION_MAP = {
    "Strong Hire": "Hire Immediately",
    "Hire": "Proceed to Interview",
    "Lean Hire": "Proceed to Interview",
    "Hold": "Further Assessment",
    "Lean No Hire": "Talent Pool",
    "No Hire": "Reject",
    "Strong Fit": "Hire Immediately",
    "Good Fit": "Proceed to Interview",
    "Consider": "Further Assessment",
    "Weak Fit": "Talent Pool",
    "Not Recommended": "Reject",
}


def _level(value: float) -> str:
    """Map a 0-100 signal to a qualitative level label."""
    if value >= 70:
        return "High"
    if value >= 45:
        return "Moderate"
    return "Low"


class ExecutiveReportBuilder:
    """Builds a unified :class:`ExecutiveHiringReport` from existing intelligence."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: AgentRunner | None = None,
        committee_engine: HiringCommitteeEngine | None = None,
        insights_fn: Any | None = None,
    ) -> None:
        """Wire the builder's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.committee_engine = committee_engine

    # -- public API ---------------------------------------------------------

    def build(
        self,
        candidate: Any = None,
        *,
        candidate_id: str | None = None,
        repository: Any = None,
        jd: str = "",
        template: str = "executive",
        mode: CommitteeMode = CommitteeMode.BALANCED,
        run_committee: bool = True,
        generated_on: str = "",
    ) -> ExecutiveHiringReport:
        """Collect all intelligence for a candidate and assemble the report."""
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
        committee_dict: dict[str, Any] = {}
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
        role_intel = self._role_intelligence(bundle.jd_analysis, jd_norm, timeline, resume)
        overview["career_story"] = timeline.get("career_story", "")

        # 4) Executive narrative via the AI Platform agent (offline composer fallback).
        payload = ExecutiveReportInput(
            candidate_id=bundle.candidate_id,
            template=template,
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
        evidence = build_executive_evidence(payload)
        narrative = self._narrative(payload, evidence)

        # 5) Synthesized presentation layers (all derived from the evidence).
        interview_strategy = self._interview_strategy(interview, recommendation, committee_dict)
        action_plan = self._action_plan(narrative, recommendation, interview, risk)
        business_intelligence = self._business_intelligence(
            intelligence, recommendation, risk, timeline, committee_dict
        )
        chart_data = charts_mod.build_chart_data(
            intelligence=intelligence,
            timeline=timeline,
            risk=risk,
            committee=committee_dict,
            interview=interview,
            resume=resume,
        )
        provenance = validators.build_provenance(narrative, evidence)

        warnings = validators.validate_provenance(provenance)
        warnings += validators.evidence_coverage_warnings(evidence)

        from src.ai.agents.executive_report.templates import get_template

        return ExecutiveHiringReport(
            report_id=self._next_report_id(bundle.candidate_id),
            candidate_id=bundle.candidate_id,
            template=template,
            audience=get_template(template).audience,
            generated_on=generated_on,
            candidate_overview=overview,
            narrative=narrative,
            resume_summary=resume.get("executive_summary", "") or "No resume analysis available.",
            jd_summary=jd_norm.get("executive_summary", "")
            or "No job description was analysed for this report.",
            role_intelligence=role_intel,
            candidate_intelligence=intelligence,
            committee=committee_dict,
            risk_dashboard=risk,
            interview_strategy=interview_strategy,
            action_plan=action_plan,
            business_intelligence=business_intelligence,
            charts=chart_data,
            provenance=provenance,
            evidence_sources=validators.available_sources(evidence),
            warnings=list(dict.fromkeys(warnings)),
        )

    # -- normalization helpers ---------------------------------------------

    @staticmethod
    def _overview(bundle: Any) -> dict[str, Any]:
        return {
            "candidate_id": bundle.candidate_id,
            "title": bundle.title,
            "company": bundle.company,
            "years_of_experience": bundle.years_of_experience,
            "location": bundle.location,
        }

    @staticmethod
    def _model_dict(model: Any) -> dict[str, Any]:
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

    def _resume(self, resume_analysis: Any) -> dict[str, Any]:
        if resume_analysis is None:
            return {}
        quality = self._model_dict(getattr(resume_analysis, "resume_quality", None))
        return {
            "executive_summary": getattr(resume_analysis, "executive_summary", ""),
            "quality": quality,
            "strengths": list(getattr(resume_analysis, "strengths", []) or []),
            "weaknesses": list(getattr(resume_analysis, "weaknesses", []) or []),
        }

    def _jd(self, jd_analysis: Any) -> dict[str, Any]:
        if jd_analysis is None:
            return {}
        return {
            "executive_summary": getattr(jd_analysis, "executive_summary", ""),
            "quality": self._model_dict(getattr(jd_analysis, "quality", None)),
        }

    def _role_intelligence(
        self,
        jd_analysis: Any,
        jd_norm: dict[str, Any],
        timeline: dict[str, Any],
        resume: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the role-intelligence display dict from the JD analysis."""
        role: dict[str, Any] = {"_timeline": timeline, "_resume_quality": resume.get("quality", {})}
        if jd_analysis is None:
            return role
        ri = self._model_dict(getattr(jd_analysis, "role_intelligence", None))
        ti = self._model_dict(getattr(jd_analysis, "technical_intelligence", None))
        hi = self._model_dict(getattr(jd_analysis, "hiring_intent", None))
        org = self._model_dict(getattr(jd_analysis, "organization_intelligence", None))
        rh = self._model_dict(getattr(jd_analysis, "requirement_hierarchy", None))
        mi = self._model_dict(getattr(jd_analysis, "market_intelligence", None))
        quality = jd_norm.get("quality", {})

        stack: list[str] = []
        for key in ("languages", "frameworks", "cloud", "ai_ml", "devops", "data"):
            stack.extend(ti.get(key, []) or [])

        clarity = quality.get("role_clarity")
        role.update(
            {
                "seniority": ri.get("seniority", ""),
                "technical_level": ri.get("technical_level", ""),
                "primary_intent": hi.get("primary_intent", ""),
                "organization_maturity": org.get("engineering_maturity")
                or org.get("company_type", ""),
                "market_competitiveness": mi.get("summary", ""),
                "role_clarity": f"{clarity:.0f}/100" if isinstance(clarity, (int, float)) else "",
                "mandatory": list(rh.get("mandatory", []) or []),
                "technology_stack": list(dict.fromkeys(stack))[:10],
                "business_priorities": list(hi.get("business_priorities", []) or []),
            }
        )
        return role

    # -- narrative ----------------------------------------------------------

    def _narrative(
        self, payload: ExecutiveReportInput, evidence: dict[str, Any]
    ) -> ExecutiveNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        try:
            result = self.ai_runner.run(executive_report_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return ExecutiveNarrative(**compose_executive_narrative(evidence))

    # -- synthesized layers (deterministic, evidence-derived) ---------------

    @staticmethod
    def _interview_strategy(
        interview: dict[str, Any], recommendation: dict[str, Any], committee: dict[str, Any]
    ) -> InterviewStrategy:
        priorities = list((committee.get("decision") or {}).get("interview_priorities", []) or [])
        focus = list(recommendation.get("interview_focus", []) or [])
        rubric = [
            "Technical depth vs. the role's mandatory stack",
            "System-design maturity appropriate to seniority",
            "Ownership, collaboration and communication",
            "Evidence for the strengths and against the concerns in this report",
        ]
        rubric = (priorities or focus) + rubric
        roadmap = [
            "Recruiter screen — motivation, logistics, comp alignment",
            "Technical interview — proven depth",
            "System design — architecture at the right scope",
            "Behavioral & leadership — collaboration and ownership",
            "Debrief & decision checkpoint",
        ]
        checkpoints = [
            "After technical: proceed only if depth is confirmed",
            "After system design: calibrate level (offer band)",
            "After debrief: committee-style go / no-go with evidence",
        ]
        post = (
            "Confirm or revise the recommendation of "
            f"'{recommendation.get('recommendation', 'the engines')}' using the interview evidence; "
            "the interview validates the concerns this report flagged rather than re-opening the ranking."
        )
        return InterviewStrategy(
            roadmap=roadmap,
            technical_interview=list(interview.get("technical_topics", []) or []),
            system_design=list(interview.get("system_design_topics", []) or []),
            behavioral_interview=list(interview.get("behavioral_questions", []) or []),
            leadership_interview=list(interview.get("leadership_questions", []) or []),
            coding_interview=list(interview.get("coding_focus", []) or []),
            evaluation_rubric=list(dict.fromkeys(rubric))[:8],
            decision_checkpoints=checkpoints,
            post_interview_recommendation=post,
        )

    @staticmethod
    def _action_plan(
        narrative: ExecutiveNarrative,
        recommendation: dict[str, Any],
        interview: dict[str, Any],
        risk: dict[str, Any],
    ) -> ExecutiveActionPlan:
        label = narrative.overall_recommendation
        primary = _ACTION_MAP.get(label, "Further Assessment")
        rationale = (
            f"Recommended disposition '{primary}' follows the '{label}' recommendation "
            "synthesized from the committee and the engines; it introduces no new ranking."
        )
        alternatives = [
            v for v in ("Proceed to Interview", "Further Assessment", "Talent Pool") if v != primary
        ][:2]
        onboarding = [
            "Assign an onboarding buddy and a 30-day ramp plan",
            "Align first project with the candidate's proven strengths",
            "Set explicit expectations for the areas this report flagged",
        ]
        val = list(risk.get("validation_questions", []) or [])
        plan_30 = ["Environment + codebase onboarding", "Ship a small, well-scoped change"] + (
            [f"Validate in practice: {val[0]}"] if val else []
        )
        plan_60 = ["Own a feature end-to-end", "Establish collaboration cadence with the team"]
        plan_90 = [
            "Take ownership of a meaningful component",
            "First performance calibration against role expectations",
        ]
        return ExecutiveActionPlan(
            primary_action=primary,
            rationale=rationale,
            alternatives=alternatives,
            onboarding_plan=onboarding,
            plan_30_day=plan_30,
            plan_60_day=plan_60,
            plan_90_day=plan_90,
        )

    @staticmethod
    def _business_intelligence(
        intelligence: dict[str, Any],
        recommendation: dict[str, Any],
        risk: dict[str, Any],
        timeline: dict[str, Any],
        committee: dict[str, Any],
    ) -> BusinessIntelligence:
        def _num(source: dict[str, Any], key: str) -> float:
            try:
                return float(source.get(key, 0.0))
            except (TypeError, ValueError):
                return 0.0

        # A single evidence-confidence figure drives every estimate's confidence.
        base_conf = (
            _num(committee.get("confidence", {}), "overall")
            or _num(intelligence, "confidence")
            or 50.0
        )

        overall = _num(intelligence, "overall_score")
        tech = _num(intelligence, "technical_score")
        lead = _num(intelligence, "leadership_score")
        growth = _num(intelligence, "career_growth_score")
        learning = _num(intelligence, "learning_velocity")
        risk_score = _num(risk, "risk_score")

        def _est(
            value: float, rationale: str, basis: list[str], *, invert: bool = False
        ) -> Estimate:
            signal = (100.0 - value) if invert else value
            return Estimate(
                level=_level(signal),
                rationale=rationale,
                confidence=round(base_conf, 1),
                basis=basis,
            )

        ci = ["Candidate Intelligence engine"]
        return BusinessIntelligence(
            business_impact=_est(
                overall,
                "Projected from the overall intelligence signal and the hiring recommendation.",
                ci + (["Hiring Recommendation engine"] if recommendation else []),
            ),
            productivity=_est(overall, "Ramp/throughput proxy from overall capability.", ci),
            technical_contribution=_est(tech, "From the technical capability signal.", ci),
            leadership_contribution=_est(lead, "From the leadership signal.", ci),
            innovation_potential=_est(
                learning,
                "From learning velocity and trajectory.",
                ci + ["Career Timeline Intelligence"],
            ),
            growth_potential=_est(
                growth, "From career-growth trajectory.", ci + ["Career Timeline Intelligence"]
            ),
            knowledge_risk=_est(
                risk_score,
                "Higher risk score implies higher knowledge/attrition risk.",
                ["Resume Risk Detection"],
                invert=True,
            ),
            team_impact=_est(
                (lead + _num(timeline, "career_stability")) / 2.0,
                "Blend of leadership signal and career stability.",
                ci + ["Career Timeline Intelligence"],
            ),
        )

    @classmethod
    def _next_report_id(cls, candidate_id: str) -> str:
        """Return a process-unique report id."""
        cls._counter += 1
        return f"exec_report_{candidate_id}_{cls._counter}"


# A shared default builder for the tool / copilot / UI.
executive_report_builder = ExecutiveReportBuilder()
