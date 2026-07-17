"""HiringComplianceAgent — Hiring Compliance Intelligence (Phase 5 / M3).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
:class:`ComplianceNarrative` from the aggregated intelligence + the compliance
signals the engine already computed. It is NOT a legal-advice system and NOT a
law engine — it identifies governance risks and human-review needs, and never
gives a legal opinion or fabricates a compliance conclusion (Module 14).

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
from typing import Any

from src.ai.agents.compliance.composer import compose_compliance_narrative
from src.ai.agents.compliance.schemas import ComplianceNarrative
from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class ComplianceInput:
    """Typed input for the HiringComplianceAgent.

    Every field is an existing engine output or a compliance signal the engine
    already computed — the agent recomputes nothing. All optional so the agent
    degrades gracefully when data is missing (Module 14).
    """

    candidate_id: str = ""
    data_available: bool = False
    candidate_overview: dict[str, Any] = field(default_factory=dict)
    evidence_sources: list[str] = field(default_factory=list)
    workflow: dict[str, Any] = field(default_factory=dict)
    approvals: dict[str, Any] = field(default_factory=dict)
    policy_checks: list[dict[str, Any]] = field(default_factory=list)
    documentation: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    governance_risk: dict[str, Any] = field(default_factory=dict)
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    review: dict[str, Any] = field(default_factory=dict)


def build_compliance_evidence(payload: ComplianceInput) -> dict[str, Any]:
    """Pack the pre-gathered outputs + computed compliance signals into evidence."""
    return {
        "candidate_overview": payload.candidate_overview or {},
        "data_available": payload.data_available,
        "evidence_sources": list(payload.evidence_sources or []),
        "workflow": payload.workflow or {},
        "approvals": payload.approvals or {},
        "policy_checks": list(payload.policy_checks or []),
        "documentation": payload.documentation or {},
        "audit": payload.audit or {},
        "governance_risk": payload.governance_risk or {},
        "exceptions": list(payload.exceptions or []),
        "review": payload.review or {},
    }


class HiringComplianceAgent(BaseAgent):
    """Surfaces hiring-governance compliance risks (never a legal opinion)."""

    metadata = AgentMetadata(
        name="hiring_compliance",
        version="v1",
        title="Hiring Compliance",
        description=(
            "Evaluates whether a hiring workflow follows company governance — "
            "required workflow steps, approval completeness, configurable policy "
            "compliance, documentation presence, audit-trail readiness and "
            "governance risk — reusing existing intelligence (committee, "
            "compensation, pay-equity, interview, executive reports). Identifies "
            "governance risks and human-review needs only; never gives legal "
            "advice, interprets law or fabricates a compliance conclusion."
        ),
        prompt_id="compliance",
        prompt_version="v1",
        tags=["compliance", "governance", "audit", "policy", "approvals", "hr", "risk"],
    )
    output_schema = ComplianceNarrative

    def build_messages(self, payload, loader, evidence: dict[str, Any]) -> list[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: ComplianceInput) -> dict[str, Any]:
        """Return the aggregated compliance evidence for ``payload``."""
        return build_compliance_evidence(payload)

    def prompt_values(self, payload: ComplianceInput, evidence: dict[str, Any]) -> dict[str, str]:
        """Supply candidate id + workflow/risk placeholders for the prompt."""
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "workflow_status": (payload.workflow or {}).get("status", "Requires Review"),
            "governance_risk": (payload.governance_risk or {}).get("level", "Medium"),
            "data_available": "yes"
            if payload.data_available
            else "no (external systems not connected)",
        }

    def cache_dimensions(self, payload: ComplianceInput) -> tuple[str, str]:
        """Cache by candidate id (subject) + full evidence signature (scope)."""
        scope = json.dumps(build_compliance_evidence(payload), sort_keys=True, default=str)
        return payload.candidate_id or "compliance", scope


def _orchestration_payload_builder(task, context) -> ComplianceInput:
    """Build a :class:`ComplianceInput` from an orchestration task + context."""
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
    return ComplianceInput(
        candidate_id=str(
            payload.get("candidate_id", "") or overview.get("candidate_id", "") or "compliance"
        ),
        data_available=bool(payload.get("data_available", False)),
        candidate_overview=overview,
        evidence_sources=payload.get("evidence_sources", []),
        workflow=payload.get("workflow", {}),
        approvals=payload.get("approvals", {}),
        policy_checks=payload.get("policy_checks", []),
        documentation=payload.get("documentation", {}),
        audit=payload.get("audit", {}),
        governance_risk=payload.get("governance_risk", {}),
        exceptions=payload.get("exceptions", []),
        review=payload.get("review", {}),
    )


def _register_with_orchestration(agent: HiringComplianceAgent) -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["hiring_compliance", "compliance", "governance_compliance"],
                payload_builder=_orchestration_payload_builder,
                name="hiring_compliance",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(ComplianceNarrative.schema_name(), compose_compliance_narrative)
compliance_agent = registry.register(HiringComplianceAgent())
_register_with_orchestration(compliance_agent)
