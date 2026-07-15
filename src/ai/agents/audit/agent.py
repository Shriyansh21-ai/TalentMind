"""HiringAuditAgent — Hiring Audit & Explainability (Phase 5 / M4).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
:class:`AuditNarrative` from the reconstructed decision journey the engine already
assembled. It reconstructs and explains — it never fabricates evidence, approvals
or history, never rewrites history and never issues a legal opinion (Module 14).

Everything infrastructural (prompt rendering, provider calls, retries,
validation, safety, caching, telemetry, deterministic fallback) comes for free
from :class:`AgentRunner`; this module only supplies the evidence packing + the
identity.

On import it auto-registers with the AI Platform agent registry, the
deterministic composer registry and the Multi-Agent Orchestration registry.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

from src.ai.agents.audit.composer import compose_audit_narrative
from src.ai.agents.audit.schemas import AuditNarrative

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class AuditInput:
    """Typed input for the HiringAuditAgent.

    Every field is a reconstructed audit artefact the engine already assembled —
    the agent recomputes nothing. All optional so the agent degrades gracefully
    when data is missing (Module 14).
    """

    candidate_id: str = ""
    data_available: bool = False
    candidate_overview: Dict[str, Any] = field(default_factory=dict)
    evidence_sources: List[str] = field(default_factory=list)
    agents_participated: List[str] = field(default_factory=list)
    decision_trace: List[Dict[str, Any]] = field(default_factory=list)
    provenance: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: Dict[str, Any] = field(default_factory=dict)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    responsibility: List[Dict[str, Any]] = field(default_factory=list)
    governance_explanations: List[Dict[str, Any]] = field(default_factory=list)
    audit_readiness: Dict[str, Any] = field(default_factory=dict)
    history: Dict[str, Any] = field(default_factory=dict)


def build_audit_evidence(payload: AuditInput) -> Dict[str, Any]:
    """Pack the reconstructed audit artefacts into the evidence dict."""
    return {
        "candidate_overview": payload.candidate_overview or {},
        "data_available": payload.data_available,
        "evidence_sources": list(payload.evidence_sources or []),
        "agents_participated": list(payload.agents_participated or []),
        "decision_trace": list(payload.decision_trace or []),
        "provenance": list(payload.provenance or []),
        "reasoning": payload.reasoning or {},
        "timeline": list(payload.timeline or []),
        "responsibility": list(payload.responsibility or []),
        "governance_explanations": list(payload.governance_explanations or []),
        "audit_readiness": payload.audit_readiness or {},
        "history": payload.history or {},
    }


class HiringAuditAgent(BaseAgent):
    """Reconstructs + explains the hiring decision journey (never fabricates)."""

    metadata = AgentMetadata(
        name="hiring_audit",
        version="v1",
        title="Hiring Audit & Explainability",
        description=(
            "Reconstructs the complete hiring journey — decision trace, evidence "
            "provenance, evidence graph, reasoning explainability, timeline, "
            "human-vs-AI responsibility, governance explanations and audit "
            "readiness — from artefacts the platform already produced (reusing the "
            "compliance/pay-equity/compensation/committee chain). Clearly separates "
            "observed facts, inferred insights, AI recommendations and human "
            "decisions; never fabricates evidence/approvals/history and never "
            "rewrites history or gives a legal opinion."
        ),
        prompt_id="audit",
        prompt_version="v1",
        tags=["audit", "explainability", "provenance", "governance", "transparency", "hr"],
    )
    output_schema = AuditNarrative

    def build_messages(self, payload, loader, evidence: Dict[str, Any]) -> List[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: AuditInput) -> Dict[str, Any]:
        """Return the reconstructed audit evidence for ``payload``."""
        return build_audit_evidence(payload)

    def prompt_values(self, payload: AuditInput, evidence: Dict[str, Any]) -> Dict[str, str]:
        """Supply candidate id + readiness/participation placeholders for the prompt."""
        readiness = payload.audit_readiness or {}
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "agents_participated": ", ".join(payload.agents_participated) or "none on record",
            "audit_readiness": f"{readiness.get('status', 'Requires Review')} ({readiness.get('readiness_level', 'Medium')})",
            "data_available": "yes" if payload.data_available else "no (archive not connected)",
        }

    def cache_dimensions(self, payload: AuditInput) -> Tuple[str, str]:
        """Cache by candidate id (subject) + full evidence signature (scope)."""
        scope = json.dumps(build_audit_evidence(payload), sort_keys=True, default=str)
        return payload.candidate_id or "audit", scope


def _orchestration_payload_builder(task, context) -> AuditInput:
    """Build an :class:`AuditInput` from an orchestration task + context."""
    payload = task.payload or {}
    overview = payload.get("candidate_overview") or {}
    if not overview and context is not None:
        candidate = getattr(context, "candidate", None)
        if candidate is not None:
            profile = getattr(candidate, "profile", None)
            overview = {
                "candidate_id": getattr(candidate, "candidate_id", ""),
                "title": getattr(profile, "current_title", ""),
            }
    return AuditInput(
        candidate_id=str(payload.get("candidate_id", "") or overview.get("candidate_id", "") or "audit"),
        data_available=bool(payload.get("data_available", False)),
        candidate_overview=overview,
        evidence_sources=payload.get("evidence_sources", []),
        agents_participated=payload.get("agents_participated", []),
        decision_trace=payload.get("decision_trace", []),
        provenance=payload.get("provenance", []),
        reasoning=payload.get("reasoning", {}),
        timeline=payload.get("timeline", []),
        responsibility=payload.get("responsibility", []),
        governance_explanations=payload.get("governance_explanations", []),
        audit_readiness=payload.get("audit_readiness", {}),
        history=payload.get("history", {}),
    )


def _register_with_orchestration(agent: "HiringAuditAgent") -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["hiring_audit", "audit", "explainability"],
                payload_builder=_orchestration_payload_builder,
                name="hiring_audit",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(AuditNarrative.schema_name(), compose_audit_narrative)
hiring_audit_agent = registry.register(HiringAuditAgent())
_register_with_orchestration(hiring_audit_agent)
