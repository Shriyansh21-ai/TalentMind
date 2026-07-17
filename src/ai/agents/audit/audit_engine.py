"""HiringAuditEngine — the collector/orchestrator (Modules 8, 12, 13).

Reuses the **Hiring Compliance** engine (which transitively reuses Pay Equity ->
Compensation Governance -> the committee -> cached ``gather_evidence``) to obtain
the entire hiring-intelligence chain in one call (Module 13 — no duplicated
reasoning), then reconstructs the decision trace (1), provenance (2), evidence
graph, reasoning (3), timeline (4), the human-vs-AI responsibility matrix (5),
governance explanations (6), audit readiness (7) and historical reconstruction (8),
and assembles the unified :class:`HiringAuditReport` (9).

It defines the future audit-archive provider interface (Module 12) — a Protocol
plus a Null default — and **implements no connector**. Without an archive, human
approvals and history are honestly reported unverified (Module 14). All
collaborators are injected (SOLID / DI).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.ai.agents.audit import approvals as approvals_mod
from src.ai.agents.audit import charts as charts_mod
from src.ai.agents.audit import decision_trace as trace_mod
from src.ai.agents.audit import evidence_graph as graph_mod
from src.ai.agents.audit import explainability as explain_mod
from src.ai.agents.audit import governance as governance_mod
from src.ai.agents.audit import history as history_mod
from src.ai.agents.audit import provenance as provenance_mod
from src.ai.agents.audit import reasoning as reasoning_mod
from src.ai.agents.audit import timeline as timeline_mod
from src.ai.agents.audit import validators
from src.ai.agents.audit.agent import AuditInput, build_audit_evidence, hiring_audit_agent
from src.ai.agents.audit.composer import compose_audit_narrative
from src.ai.agents.audit.schemas import AuditNarrative, HiringAuditReport
from src.ai.agents.audit.templates import AGENT_CATALOG
from src.ai.agents.compliance.compliance_report import HiringComplianceEngine
from src.ai.committee.schemas import CommitteeMode
from src.ai.core.runner import AgentRunner

# ---------------------------------------------------------------------------
# Module 12 — future audit-archive provider interface (interface only)
# ---------------------------------------------------------------------------


@runtime_checkable
class AuditArchiveProvider(Protocol):
    """Future audit/archive integration seam (Module 12 — interface only).

    A real implementation (SIEM, document-management system, compliance archive,
    audit system, enterprise data lake) returns the stored history + verified
    approvals for a candidate. TalentMind implements none of these; the Protocol
    exists so a later milestone plugs one in without a redesign.
    """

    def is_available(self) -> bool:
        """Return True when a live audit archive can be served."""
        ...

    def get_history(self, candidate_id: str) -> list[dict[str, Any]] | None:
        """Return stored historical decision records or ``None``."""
        ...


class NullAuditArchiveProvider:
    """Default provider: no audit archive (the shipped behaviour)."""

    def is_available(self) -> bool:
        """Always False — no audit archive is connected."""
        return False

    def get_history(self, candidate_id: str) -> list[dict[str, Any]] | None:
        """Return ``None`` — no history available."""
        return None


class HiringAuditEngine:
    """Builds a unified :class:`HiringAuditReport` from existing artefacts."""

    _counter = 0

    def __init__(
        self,
        *,
        ai_runner: AgentRunner | None = None,
        compliance_engine: HiringComplianceEngine | None = None,
        insights_fn: Any | None = None,
        compliance_provider: Any | None = None,
        archive_provider: AuditArchiveProvider | None = None,
    ) -> None:
        """Wire the engine's collaborators (all optional; sane defaults used)."""
        self.ai_runner = ai_runner or AgentRunner()
        self.insights_fn = insights_fn
        self.compliance_engine = compliance_engine
        self.compliance_provider = compliance_provider
        self.archive_provider = archive_provider or NullAuditArchiveProvider()

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
    ) -> HiringAuditReport:
        """Reconstruct the full hiring journey and assemble the audit report."""
        if candidate is None:
            if repository is None or candidate_id is None:
                raise ValueError("Provide a candidate, or a repository + candidate_id.")
            candidate = repository.get(candidate_id)
            if candidate is None:
                raise ValueError(f"Unknown candidate {candidate_id!r}.")
        if isinstance(mode, str):
            mode = CommitteeMode(mode)

        # 1) Reuse the Hiring Compliance engine for the whole chain (Module 13).
        compliance_engine = self.compliance_engine or HiringComplianceEngine(
            insights_fn=self.insights_fn,
            ai_runner=self.ai_runner,
            data_provider=self.compliance_provider,
        )
        compliance_report = compliance_engine.build(
            candidate=candidate, jd=jd, mode=mode, generated_on=generated_on
        )
        cr = compliance_report.to_dict()

        archive_available = bool(getattr(self.archive_provider, "is_available", lambda: False)())

        # 2) Build the shared audit context from the reused compliance report.
        evidence_sources = list(
            dict.fromkeys(list(compliance_report.evidence_sources) + ["Hiring Compliance"])
        )
        agents_participated = [
            e.origin_agent for e in AGENT_CATALOG if e.source in set(evidence_sources)
        ]
        context: dict[str, Any] = {
            "candidate_id": compliance_report.candidate_id,
            "overview": compliance_report.candidate_overview,
            "evidence_sources": evidence_sources,
            "workflow": cr.get("workflow", {}),
            "approvals": cr.get("approvals", {}),
            "documentation": cr.get("documentation", {}),
            "audit": cr.get("audit", {}),
            "governance_risk": cr.get("governance_risk", {}),
            "exceptions": cr.get("exceptions", []),
            "policy_checks": cr.get("policy_checks", []),
            "review": cr.get("review", {}),
            "equity_risk_level": self._equity_level(cr),
            "data_available": archive_available,  # audit-archive availability (history/approvals)
        }

        # 3) Deterministic reconstruction layers.
        decision_trace = trace_mod.build_decision_trace(context)
        provenance = provenance_mod.build_provenance(context)
        evidence_graph = graph_mod.build_evidence_graph(context)
        reasoning = reasoning_mod.build_reasoning(context)
        timeline = timeline_mod.build_timeline(context)
        responsibility = approvals_mod.build_responsibility_matrix(context)
        governance_explanations = explain_mod.build_governance_explanations(context)
        audit_readiness = governance_mod.build_audit_readiness(context)
        history = history_mod.reconstruct_history(
            compliance_report.candidate_id, self.archive_provider
        )

        # 4) Narrative via the AI Platform agent (offline composer fallback).
        payload = AuditInput(
            candidate_id=compliance_report.candidate_id,
            data_available=archive_available,
            candidate_overview=compliance_report.candidate_overview,
            evidence_sources=evidence_sources,
            agents_participated=agents_participated,
            decision_trace=[s.to_dict() for s in decision_trace],
            provenance=[p.to_dict() for p in provenance],
            reasoning=reasoning.to_dict(),
            timeline=[t.to_dict() for t in timeline],
            responsibility=[r.to_dict() for r in responsibility],
            governance_explanations=[g.to_dict() for g in governance_explanations],
            audit_readiness=audit_readiness.to_dict(),
            history=history.to_dict(),
        )
        evidence = build_audit_evidence(payload)
        narrative = self._narrative(payload, evidence)

        chart_data = charts_mod.build_chart_data(
            decision_trace=decision_trace,
            evidence_graph=evidence_graph,
            timeline=timeline,
            responsibility=responsibility,
            readiness=audit_readiness,
            agents_participated=agents_participated,
        )

        warnings = validators.evidence_coverage_warnings(evidence)
        warnings += validators.validate_safety(
            narrative, responsibility, history, archive_available
        )

        return HiringAuditReport(
            report_id=self._next_report_id(compliance_report.candidate_id),
            candidate_id=compliance_report.candidate_id,
            generated_on=generated_on,
            data_available=archive_available,
            candidate_overview=compliance_report.candidate_overview,
            narrative=narrative,
            decision_trace=decision_trace,
            provenance=provenance,
            evidence_graph=evidence_graph,
            reasoning=reasoning,
            timeline=timeline,
            responsibility=responsibility,
            governance_explanations=governance_explanations,
            audit_readiness=audit_readiness,
            history=history,
            charts=chart_data,
            evidence_sources=evidence_sources,
            agents_participated=agents_participated,
            warnings=list(dict.fromkeys(warnings)),
        )

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _equity_level(cr: dict[str, Any]) -> str:
        """Best-effort pull of the pay-equity risk level from an exception, if any."""
        for e in cr.get("exceptions", []):
            if "Pay-equity" in e.get("kind", ""):
                return "High"
        return "Unknown"

    def _narrative(self, payload: AuditInput, evidence: dict[str, Any]) -> AuditNarrative:
        """Run the agent; fall back to the deterministic composer on any failure."""
        try:
            result = self.ai_runner.run(hiring_audit_agent, payload)
            if result.ok and result.data is not None:
                return result.data
        except Exception:
            pass
        return AuditNarrative(**compose_audit_narrative(evidence))

    @classmethod
    def _next_report_id(cls, candidate_id: str) -> str:
        """Return a process-unique report id."""
        cls._counter += 1
        return f"audit_{candidate_id}_{cls._counter}"


# A shared default engine for the tool / copilot / UI.
hiring_audit_engine = HiringAuditEngine()
