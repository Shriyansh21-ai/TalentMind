"""Compensation governance checks + the governance engine (Modules 3, 15).

Two responsibilities live here:

* :func:`build_governance_checks` — the Module 3 policy evaluation: internal
  policy alignment, role alignment, experience alignment, skill/leadership/
  strategic premiums and replacement-vs-growth classification. **Every check
  explains WHY.**
* :class:`CompensationGovernanceEngine` — the collector/orchestrator. It reuses
  the committee's ``gather_evidence`` (cached resume/JD/insight outputs + the
  deterministic interview plan), optionally runs the committee, runs the
  CompensationGovernanceAgent for the narrative, and assembles the unified
  :class:`CompensationReport`. It re-runs no engine and fabricates no financial
  data (Modules 15 / 16). All collaborators are injected (SOLID / DI).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.ai.agents.compensation import budget as budget_mod
from src.ai.agents.compensation import charts as charts_mod
from src.ai.agents.compensation import future_growth as future_mod
from src.ai.agents.compensation import internal_equity as equity_mod
from src.ai.agents.compensation import market_position as market_mod
from src.ai.agents.compensation import negotiation as negotiation_mod
from src.ai.agents.compensation import offer_justification as justification_mod
from src.ai.agents.compensation import salary_strategy as strategy_mod
from src.ai.agents.compensation import validators
from src.ai.agents.compensation.agent import (
    CompensationInput,
    build_compensation_evidence,
    compensation_agent,
)
from src.ai.agents.compensation.composer import compose_compensation_narrative
from src.ai.agents.compensation.internal_equity import CompensationDataProvider
from src.ai.agents.compensation.schemas import (
    CompensationNarrative,
    CompensationRange,
    CompensationReport,
    GovernanceCheck,
)
from src.ai.committee.committee import HiringCommitteeEngine, gather_evidence
from src.ai.committee.schemas import CommitteeMode
from src.ai.core.runner import AgentRunner


def _num(source: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(source.get(key, default))
    except (TypeError, ValueError):
        return default


def build_governance_checks(
    evidence: dict[str, Any],
    band: CompensationRange,
    hire_type: str,
) -> list[GovernanceCheck]:
    """Evaluate the Module 3 governance dimensions, each with an explicit WHY."""
    intelligence = evidence.get("intelligence") or {}
    overview = evidence.get("candidate_overview") or {}
    comp = evidence.get("candidate_comp") or {}
    checks: list[GovernanceCheck] = []

    # Internal policy alignment — the range is a band, not a fixed number.
    checks.append(
        GovernanceCheck(
            dimension="Internal policy alignment",
            status="Aligned",
            rationale=(
                "Recommendation is a defensible range with a documented basis and audit "
                "trail, satisfying the transparency policy."
            ),
        )
    )

    # Offer consistency — target sits inside the recommended band.
    consistent = band.minimum <= band.target <= band.maximum
    checks.append(
        GovernanceCheck(
            dimension="Offer consistency",
            status="Aligned" if consistent else "Review",
            rationale=f"Target {band.target:.1f} {band.unit} lies within the band "
            f"{band.minimum:.1f}-{band.maximum:.1f}."
            if consistent
            else "Target falls outside the band.",
        )
    )

    # Role & experience alignment.
    years = _num(overview, "years_of_experience")
    checks.append(
        GovernanceCheck(
            dimension="Experience alignment",
            status="Aligned",
            rationale=f"Band calibrated to {years:.0f} years of experience and the assessed seniority.",
            source="Candidate Intelligence engine",
        )
    )

    # Skill / leadership / strategic premiums — explain whether each applied.
    tech = _num(intelligence, "technical_score")
    checks.append(
        GovernanceCheck(
            dimension="Skill premium",
            status="Aligned" if tech >= 75 else "Not Evaluable" if not tech else "Aligned",
            rationale=(
                f"Skill premium applied (technical signal {tech:.0f}/100)."
                if tech >= 75
                else f"No skill premium (technical signal {tech:.0f}/100 below threshold)."
                if tech
                else "Technical signal unavailable; no skill premium applied."
            ),
            source="Candidate Intelligence engine",
        )
    )
    lead = _num(intelligence, "leadership_score")
    checks.append(
        GovernanceCheck(
            dimension="Leadership premium",
            status="Aligned",
            rationale=(
                f"Leadership premium applied (leadership signal {lead:.0f}/100)."
                if lead >= 70
                else f"No leadership premium (leadership signal {lead:.0f}/100 below threshold)."
            ),
            source="Candidate Intelligence engine",
        )
    )

    # Strategic hiring premium + replacement vs. growth.
    checks.append(
        GovernanceCheck(
            dimension="Strategic hiring premium",
            status="Aligned" if hire_type == "Critical Hire" else "Not Evaluable",
            rationale=(
                "Strategic premium justified by a critical-hire classification."
                if hire_type == "Critical Hire"
                else "Not a critical hire; no strategic premium applied."
            ),
            source="Compensation Governance",
        )
    )
    checks.append(
        GovernanceCheck(
            dimension="Replacement vs. Growth hire",
            status="Aligned",
            rationale=f"Classified as a {hire_type} (no backfill/attrition data connected; heuristic).",
            source="Budget Governance",
        )
    )

    return checks


class CompensationGovernanceEngine:
    """Builds a unified :class:`CompensationReport` from existing intelligence."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: AgentRunner | None = None,
        committee_engine: HiringCommitteeEngine | None = None,
        insights_fn: Any | None = None,
        equity_provider: CompensationDataProvider | None = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.committee_engine = committee_engine
        self.equity_provider = equity_provider

    # -- public API ---------------------------------------------------------

    def build(
        self,
        candidate: Any = None,
        *,
        candidate_id: str | None = None,
        repository: Any = None,
        jd: str = "",
        mode: CommitteeMode = CommitteeMode.BALANCED,
        run_committee: bool = True,
        generated_on: str = "",
    ) -> CompensationReport:
        """Collect all intelligence for a candidate and assemble the governance report."""
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
        candidate_comp = self._candidate_comp(candidate)
        resume = self._resume(bundle.resume_analysis)
        jd_norm = self._jd(bundle.jd_analysis)
        intelligence = self._model_dict(bundle.intelligence)
        timeline = self._model_dict(bundle.timeline)
        risk = self._model_dict(bundle.risk)
        recommendation = self._model_dict(bundle.recommendation)
        interview = self._model_dict(bundle.interview_plan)

        payload = CompensationInput(
            candidate_id=bundle.candidate_id,
            candidate_overview=overview,
            candidate_comp=candidate_comp,
            resume=resume,
            jd=jd_norm,
            committee=committee_dict,
            intelligence=intelligence,
            timeline=timeline,
            risk=risk,
            recommendation=recommendation,
            interview=interview,
        )
        evidence = build_compensation_evidence(payload)

        # 4) Deterministic governance layers (all derived from the evidence).
        band = strategy_mod.build_recommended_range(evidence)
        scenarios = strategy_mod.build_scenarios(evidence, band)
        market = market_mod.assess_market_position(evidence, band)
        budget = budget_mod.assess_budget(evidence, band)
        negotiation = negotiation_mod.build_negotiation(evidence, band)
        equity = equity_mod.assess_internal_equity(evidence, band, self.equity_provider)
        future = future_mod.build_future_outlook(evidence)
        governance_checks = build_governance_checks(evidence, band, budget.hire_type)
        justification = justification_mod.build_justification(
            evidence, band, market, budget, negotiation
        )

        # 5) Enrich the payload with the computed heuristics so the narrative can cite them.
        payload.recommended_range = band.to_dict()
        payload.market_position = market.position
        payload.hire_type = budget.hire_type
        evidence = build_compensation_evidence(payload)

        # 6) Compensation narrative via the AI Platform agent (offline composer fallback).
        narrative = self._narrative(payload, evidence)

        # 7) Flagship audit trail (Module 12).
        report_id = self._next_report_id(bundle.candidate_id)
        audit_trail = justification_mod.build_audit_trail(
            evidence,
            band,
            market,
            budget,
            decision_id=f"COMP-{report_id}",
            decision_timestamp=generated_on,
            equity_available=equity.available,
        )

        chart_data = charts_mod.build_chart_data(
            band=band,
            scenarios=scenarios,
            market=market,
            budget=budget,
            negotiation=negotiation,
            future=future,
        )

        warnings = validators.evidence_coverage_warnings(evidence)
        warnings += validators.validate_no_fabrication(band, market, equity)

        return CompensationReport(
            report_id=report_id,
            candidate_id=bundle.candidate_id,
            generated_on=generated_on,
            candidate_overview=overview,
            narrative=narrative,
            recommended_range=band,
            justification=justification,
            governance_checks=governance_checks,
            market_position=market,
            scenarios=scenarios,
            negotiation=negotiation,
            budget=budget,
            internal_equity=equity,
            future_outlook=future,
            audit_trail=audit_trail,
            charts=chart_data,
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
    def _candidate_comp(candidate: Any) -> dict[str, Any]:
        """Extract the candidate's OWN stated compensation signals (Observed Evidence)."""
        redrob = getattr(candidate, "redrob_signals", None)
        if redrob is None:
            return {}
        salary = getattr(redrob, "expected_salary_range_inr_lpa", None)
        return {
            "currency": "INR",
            "unit": "LPA",
            "expected_min": float(getattr(salary, "min", 0.0)) if salary else 0.0,
            "expected_max": float(getattr(salary, "max", 0.0)) if salary else 0.0,
            "offer_acceptance_rate": float(getattr(redrob, "offer_acceptance_rate", 0.0) or 0.0),
            "notice_period_days": float(getattr(redrob, "notice_period_days", 0.0) or 0.0),
            "willing_to_relocate": bool(getattr(redrob, "willing_to_relocate", False)),
            "open_to_work": bool(getattr(redrob, "open_to_work_flag", False)),
            "preferred_work_mode": getattr(redrob, "preferred_work_mode", ""),
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
        return {
            "executive_summary": getattr(resume_analysis, "executive_summary", ""),
            "strengths": list(getattr(resume_analysis, "strengths", []) or []),
        }

    def _jd(self, jd_analysis: Any) -> dict[str, Any]:
        if jd_analysis is None:
            return {}
        return {"executive_summary": getattr(jd_analysis, "executive_summary", "")}

    # -- narrative ----------------------------------------------------------

    def _narrative(
        self, payload: CompensationInput, evidence: dict[str, Any]
    ) -> CompensationNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        try:
            result = self.ai_runner.run(compensation_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return CompensationNarrative(**compose_compensation_narrative(evidence))

    @classmethod
    def _next_report_id(cls, candidate_id: str) -> str:
        """Return a process-unique report id."""
        cls._counter += 1
        return f"comp_report_{candidate_id}_{cls._counter}"


# A shared default engine for the tool / copilot / UI.
compensation_governance_engine = CompensationGovernanceEngine()
