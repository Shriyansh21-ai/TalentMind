"""HiringComplianceEngine — the collector/orchestrator (Modules 8, 12, 13).

Reuses the **Pay Equity Guardian** (which transitively reuses Compensation
Governance + the committee + cached ``gather_evidence``) to obtain the full
hiring-intelligence chain in one call (Module 13 — no duplicated reasoning), then
evaluates workflow compliance (1), approvals (2), policy (3), documentation (4),
governance risk (5), audit trail (6), exceptions (7), the review determination and
scenarios (9), and assembles the unified :class:`HiringComplianceReport` (8).

It defines the future governance/document/workflow data-provider interface
(Module 12) — a Protocol plus a Null default — and **implements no integration**.
Without a provider, approvals/documents that need an external system are honestly
reported pending review (Module 14). All collaborators are injected (SOLID / DI).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.ai.agents.compliance import approval_engine as approval_mod
from src.ai.agents.compliance import audit as audit_mod
from src.ai.agents.compliance import charts as charts_mod
from src.ai.agents.compliance import documentation as documentation_mod
from src.ai.agents.compliance import exceptions as exceptions_mod
from src.ai.agents.compliance import governance as governance_mod
from src.ai.agents.compliance import policy_engine as policy_mod
from src.ai.agents.compliance import review as review_mod
from src.ai.agents.compliance import risk as risk_mod
from src.ai.agents.compliance import validators
from src.ai.agents.compliance import workflow as workflow_mod
from src.ai.agents.compliance.agent import (
    ComplianceInput,
    build_compliance_evidence,
    compliance_agent,
)
from src.ai.agents.compliance.composer import compose_compliance_narrative
from src.ai.agents.compliance.schemas import ComplianceNarrative, HiringComplianceReport
from src.ai.agents.compliance.templates import COMPLIANCE_THRESHOLDS, list_policies
from src.ai.agents.pay_equity.equity_engine import PayEquityGuardianEngine
from src.ai.committee.schemas import CommitteeMode
from src.ai.core.runner import AgentRunner

# ---------------------------------------------------------------------------
# Module 12 — future governance/document/workflow provider (interface only)
# ---------------------------------------------------------------------------


@runtime_checkable
class ComplianceDataProvider(Protocol):
    """Future governance/document/workflow integration seam (Module 12 — interface only).

    A real implementation (ISO/SOC2 evidence store, internal governance system,
    document-management system, HR policy engine, workflow system) confirms which
    approvals/documents exist and returns the audit history. TalentMind implements
    none of these; the Protocol exists so a later milestone plugs one in without a
    redesign.
    """

    def is_available(self) -> bool:
        """Return True when live governance/workflow data can be served."""
        ...

    def get_approvals(self, candidate_id: str) -> dict[str, dict[str, Any]] | None:
        """Return ``{role: {approved, by, at}}`` or ``None``."""
        ...

    def get_documents(self, candidate_id: str) -> dict[str, bool] | None:
        """Return ``{document_key: present}`` or ``None``."""
        ...

    def get_audit_events(self, candidate_id: str) -> list[dict[str, Any]] | None:
        """Return the recorded audit events or ``None``."""
        ...


class NullComplianceDataProvider:
    """Default provider: no governance/workflow data (the shipped behaviour)."""

    def is_available(self) -> bool:
        """Always False — no governance/workflow system is connected."""
        return False

    def get_approvals(self, candidate_id: str) -> dict[str, dict[str, Any]] | None:
        """Return ``None`` — no approval data available."""
        return None

    def get_documents(self, candidate_id: str) -> dict[str, bool] | None:
        """Return ``None`` — no document data available."""
        return None

    def get_audit_events(self, candidate_id: str) -> list[dict[str, Any]] | None:
        """Return ``None`` — no audit events available."""
        return None


class HiringComplianceEngine:
    """Builds a unified :class:`HiringComplianceReport` from existing intelligence."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: AgentRunner | None = None,
        pay_equity_engine: PayEquityGuardianEngine | None = None,
        insights_fn: Any | None = None,
        data_provider: ComplianceDataProvider | None = None,
        policies: list[Any] | None = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.pay_equity_engine = pay_equity_engine
        self.data_provider = data_provider or NullComplianceDataProvider()
        self.policies = policies if policies is not None else list_policies()

    # -- public API ---------------------------------------------------------

    def build(
        self,
        candidate: Any = None,
        *,
        candidate_id: str | None = None,
        repository: Any = None,
        jd: str = "",
        mode: CommitteeMode = CommitteeMode.BALANCED,
        generated_on: str = "",
    ) -> HiringComplianceReport:
        """Collect the full intelligence chain and assemble the compliance report."""
        if candidate is None:
            if repository is None or candidate_id is None:
                raise ValueError("Provide a candidate, or a repository + candidate_id.")
            candidate = repository.get(candidate_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate {candidate_id!r}.")
        if isinstance(mode, str):
            mode = CommitteeMode(mode)

        # 1) Reuse the Pay Equity Guardian for the whole chain (Module 13).
        pe_engine = self.pay_equity_engine or PayEquityGuardianEngine(
            insights_fn=self.insights_fn, ai_runner=self.ai_runner
        )
        pe_report = pe_engine.build(
            candidate=candidate, jd=jd, mode=mode, generated_on=generated_on
        )

        provider = self.data_provider
        data_available = bool(getattr(provider, "is_available", lambda: False)())

        # 2) Build the shared compliance context from the reused report.
        context = self._context(pe_report, candidate, data_available)

        # 3) Deterministic compliance layers.
        documentation = documentation_mod.validate_documentation(context, provider)
        approvals = approval_mod.build_approval_matrix(context, provider)
        workflow = workflow_mod.assess_workflow(context, approvals, documentation)
        policy_checks = policy_mod.evaluate_policies(self.policies, context, approvals)
        audit = audit_mod.validate_audit_trail(context, approvals, provider)
        exceptions = exceptions_mod.detect_exceptions(
            context, workflow, approvals, documentation, policy_checks
        )
        governance_risk = risk_mod.assess_governance_risk(
            workflow, exceptions, approvals, documentation
        )
        review = review_mod.determine_review(governance_risk, exceptions, policy_checks)
        scenarios = governance_mod.build_scenarios(context)

        # 4) Narrative via the AI Platform agent (offline composer fallback).
        payload = ComplianceInput(
            candidate_id=pe_report.candidate_id,
            data_available=data_available,
            candidate_overview=pe_report.candidate_overview,
            evidence_sources=context["evidence_sources"],
            workflow=workflow.to_dict(),
            approvals=approvals.to_dict(),
            policy_checks=[p.to_dict() for p in policy_checks],
            documentation=documentation.to_dict(),
            audit=audit.to_dict(),
            governance_risk=governance_risk.to_dict(),
            exceptions=[e.to_dict() for e in exceptions],
            review=review.to_dict(),
        )
        evidence = build_compliance_evidence(payload)
        narrative = self._narrative(payload, evidence)

        chart_data = charts_mod.build_chart_data(
            workflow=workflow,
            approvals=approvals,
            documentation=documentation,
            audit=audit,
            governance_risk=governance_risk,
        )

        warnings = validators.evidence_coverage_warnings(evidence)
        warnings += validators.validate_safety(narrative, approvals, data_available)

        return HiringComplianceReport(
            report_id=self._next_report_id(pe_report.candidate_id),
            candidate_id=pe_report.candidate_id,
            generated_on=generated_on,
            data_available=data_available,
            candidate_overview=pe_report.candidate_overview,
            narrative=narrative,
            workflow=workflow,
            approvals=approvals,
            policy_checks=policy_checks,
            documentation=documentation,
            audit=audit,
            governance_risk=governance_risk,
            exceptions=exceptions,
            review=review,
            scenarios=scenarios,
            charts=chart_data,
            evidence_sources=context["evidence_sources"],
            warnings=list(dict.fromkeys(warnings)),
        )

    # -- context ------------------------------------------------------------

    @staticmethod
    def _context(pe_report: Any, candidate: Any, data_available: bool) -> dict[str, Any]:
        """Build the shared compliance context from the reused pay-equity report."""
        overview = pe_report.candidate_overview
        offer = pe_report.offer_summary
        hire_type = offer.get("hire_type", "")
        # Required approvers + reasons reused from the pay-equity executive review.
        er = pe_report.executive_review
        required_approvers = er.required_approvers()
        approval_reasons = {a.approver: a.reason for a in er.approvals}

        redrob = getattr(candidate, "redrob_signals", None)
        work_mode = str(getattr(redrob, "preferred_work_mode", "")).lower() if redrob else ""
        comp_target = float(offer.get("target", 0.0) or 0.0)
        threshold = COMPLIANCE_THRESHOLDS["finance_salary_threshold_lpa"]

        # The pay-equity guardian (and thus compensation governance) definitely ran
        # — ensure both are represented in the evidence sources the compliance layer
        # derives workflow/document presence from.
        evidence_sources = list(
            dict.fromkeys(
                list(pe_report.evidence_sources)
                + ["Compensation Governance Agent", "Pay Equity Guardian"]
            )
        )

        return {
            "candidate_id": pe_report.candidate_id,
            "overview": overview,
            "evidence_sources": evidence_sources,
            "hire_type": hire_type,
            "market_position": offer.get("market_position", ""),
            "comp_target": comp_target,
            "required_approvers": required_approvers,
            "approval_reasons": approval_reasons,
            "executive_hire": hire_type == "Critical Hire" or "Executive" in required_approvers,
            "critical_hire": hire_type == "Critical Hire",
            "salary_above_threshold": comp_target > threshold,
            "remote_hire": "remote" in work_mode,
            "equity_risk_level": pe_report.equity_risk.level,
            "pay_policy_alignment": pe_report.policy_alignment.alignment,
        }

    # -- narrative ----------------------------------------------------------

    def _narrative(self, payload: ComplianceInput, evidence: dict[str, Any]) -> ComplianceNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        try:
            result = self.ai_runner.run(compliance_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return ComplianceNarrative(**compose_compliance_narrative(evidence))

    @classmethod
    def _next_report_id(cls, candidate_id: str) -> str:
        """Return a process-unique report id."""
        cls._counter += 1
        return f"compliance_{candidate_id}_{cls._counter}"


# A shared default engine for the tool / copilot / UI.
hiring_compliance_engine = HiringComplianceEngine()
