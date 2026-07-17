"""Visualization data for the Audit dashboard (Module 10).

Pure data builders (no plotting, no Streamlit import): a decision-flow view, the
evidence graph, the timeline, the approval chain, agent participation, governance
health and audit readiness. Every value is a status or a coverage count — never a
fabricated figure.
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.audit.schemas import (
    AuditReadiness,
    DecisionResponsibility,
    DecisionTraceStep,
    EvidenceGraph,
    TimelineEvent,
)

_READINESS_INDEX = {"high": 3, "medium": 2, "low": 1}


def build_chart_data(
    *,
    decision_trace: list[DecisionTraceStep],
    evidence_graph: EvidenceGraph,
    timeline: list[TimelineEvent],
    responsibility: list[DecisionResponsibility],
    readiness: AuditReadiness,
    agents_participated: list[str],
) -> dict[str, Any]:
    """Build every chart structure for the audit dashboard (Module 10)."""
    total_agents = len({n.id for n in evidence_graph.nodes if n.kind == "agent"})
    return {
        "decision_flow": [
            {"stage": s.stage, "status": s.status, "order": s.order} for s in decision_trace
        ],
        "evidence_graph": evidence_graph.to_dict(),
        "timeline": [
            {"order": t.order, "name": t.name, "actor": t.actor, "status": t.status}
            for t in timeline
        ],
        "approval_chain": [
            {"decision": d.decision, "party": d.responsible_party, "status": d.status}
            for d in responsibility
            if d.responsible_party != "AI"
        ],
        "agent_participation": {
            "participated": list(agents_participated),
            "count": len(agents_participated),
            "total": total_agents,
            "ratio": round(len(agents_participated) / total_agents, 3) if total_agents else 0.0,
        },
        "governance_health": {
            "readiness": readiness.readiness_level,
            "index": _READINESS_INDEX.get(readiness.readiness_level.lower(), 2),
            "scale": ["Low", "Medium", "High"],
        },
        "audit_readiness": {
            "status": readiness.status,
            "missing_evidence": len(readiness.missing_evidence),
            "missing_documents": len(readiness.missing_documents),
            "missing_approvals": len(readiness.missing_approvals),
            "unverified_decisions": len(readiness.unverified_decisions),
        },
    }
