"""PayEquityGuardianAgent — Internal Pay Equity & Fairness (Phase 5 / M2).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
:class:`PayEquityNarrative` from the aggregated intelligence + the pay-equity
signals the engine already computed. It is NOT a bias detector and NOT a legal
decision engine — it surfaces internal-fairness governance risks and human-review
needs, and never fabricates payroll or concludes a legal violation (Module 14).

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

from src.ai.agents.pay_equity.composer import compose_pay_equity_narrative
from src.ai.agents.pay_equity.schemas import PayEquityNarrative

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class PayEquityInput:
    """Typed input for the PayEquityGuardianAgent.

    Every field is an existing engine output or a pay-equity signal the engine
    already computed — the agent recomputes nothing. All optional so the agent
    degrades gracefully when internal data is missing (Module 14).
    """

    candidate_id: str = ""
    policy_name: str = ""
    data_available: bool = False
    candidate_overview: Dict[str, Any] = field(default_factory=dict)
    offer_summary: Dict[str, Any] = field(default_factory=dict)
    compensation: Dict[str, Any] = field(default_factory=dict)
    intelligence: Dict[str, Any] = field(default_factory=dict)
    timeline: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    committee: Dict[str, Any] = field(default_factory=dict)
    recommendation: Dict[str, Any] = field(default_factory=dict)
    internal_data: Dict[str, Any] = field(default_factory=dict)
    # Computed pay-equity signals (so the narrative can cite them).
    equity_risk: Dict[str, Any] = field(default_factory=dict)
    compression: Dict[str, Any] = field(default_factory=dict)
    inversion: Dict[str, Any] = field(default_factory=dict)
    promotion: Dict[str, Any] = field(default_factory=dict)
    policy_alignment: Dict[str, Any] = field(default_factory=dict)
    fairness: Dict[str, Any] = field(default_factory=dict)
    executive_review: Dict[str, Any] = field(default_factory=dict)


def build_pay_equity_evidence(payload: PayEquityInput) -> Dict[str, Any]:
    """Pack the pre-gathered structured outputs + computed signals into evidence."""
    return {
        "candidate_overview": payload.candidate_overview or {},
        "offer_summary": payload.offer_summary or {},
        "policy_name": payload.policy_name,
        "data_available": payload.data_available,
        "compensation": payload.compensation or {},
        "intelligence": payload.intelligence or {},
        "timeline": payload.timeline or {},
        "risk": payload.risk or {},
        "committee": payload.committee or {},
        "recommendation": payload.recommendation or {},
        "internal_data": payload.internal_data or {},
        "equity_risk": payload.equity_risk or {},
        "compression": payload.compression or {},
        "inversion": payload.inversion or {},
        "promotion": payload.promotion or {},
        "policy_alignment": payload.policy_alignment or {},
        "fairness": payload.fairness or {},
        "executive_review": payload.executive_review or {},
    }


class PayEquityGuardianAgent(BaseAgent):
    """Surfaces internal-fairness governance risks (never a legal / bias conclusion)."""

    metadata = AgentMetadata(
        name="pay_equity_guardian",
        version="v1",
        title="Pay Equity Guardian",
        description=(
            "Evaluates whether an offer is internally fair — salary compression, "
            "pay inversion, promotion equity, company pay-policy alignment and "
            "executive-review needs — using existing intelligence and (when "
            "connected) internal compensation data. Surfaces governance risks and "
            "human-review needs only; never fabricates payroll, never accuses "
            "discrimination and never concludes a legal violation."
        ),
        prompt_id="pay_equity",
        prompt_version="v1",
        tags=["pay-equity", "fairness", "governance", "compliance", "hr", "compression"],
    )
    output_schema = PayEquityNarrative

    def build_messages(self, payload, loader, evidence: Dict[str, Any]) -> List[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: PayEquityInput) -> Dict[str, Any]:
        """Return the aggregated pay-equity evidence for ``payload``."""
        return build_pay_equity_evidence(payload)

    def prompt_values(self, payload: PayEquityInput, evidence: Dict[str, Any]) -> Dict[str, str]:
        """Supply candidate id + offer/policy placeholders for the prompt."""
        offer = payload.offer_summary or {}
        offer_str = offer.get("recommended_range") or (
            f"{offer.get('currency', 'INR')} target {offer.get('target', 0)} {offer.get('unit', 'LPA')}"
        )
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "offer_summary": offer_str,
            "policy_name": payload.policy_name or "Pay-Band First",
            "data_available": "yes" if payload.data_available else "no (internal data unavailable)",
        }

    def cache_dimensions(self, payload: PayEquityInput) -> Tuple[str, str]:
        """Cache by candidate id (subject) + full evidence signature (scope)."""
        scope = json.dumps(build_pay_equity_evidence(payload), sort_keys=True, default=str)
        return payload.candidate_id or "pay_equity", scope


def _orchestration_payload_builder(task, context) -> PayEquityInput:
    """Build a :class:`PayEquityInput` from an orchestration task + context."""
    payload = task.payload or {}
    overview = payload.get("candidate_overview") or {}
    if not overview and context is not None:
        candidate = getattr(context, "candidate", None)
        if candidate is not None:
            profile = getattr(candidate, "profile", None)
            overview = {
                "candidate_id": getattr(candidate, "candidate_id", ""),
                "title": getattr(profile, "current_title", ""),
                "years_of_experience": getattr(profile, "years_of_experience", 0.0),
            }
    return PayEquityInput(
        candidate_id=str(payload.get("candidate_id", "") or overview.get("candidate_id", "") or "pay_equity"),
        policy_name=payload.get("policy_name", ""),
        data_available=bool(payload.get("data_available", False)),
        candidate_overview=overview,
        offer_summary=payload.get("offer_summary", {}),
        compensation=payload.get("compensation", {}),
        intelligence=payload.get("intelligence", {}),
        timeline=payload.get("timeline", {}),
        risk=payload.get("risk", {}),
        committee=payload.get("committee", {}),
        recommendation=payload.get("recommendation", {}),
    )


def _register_with_orchestration(agent: "PayEquityGuardianAgent") -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["pay_equity_guardian", "pay_equity", "internal_equity"],
                payload_builder=_orchestration_payload_builder,
                name="pay_equity_guardian",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(PayEquityNarrative.schema_name(), compose_pay_equity_narrative)
pay_equity_agent = registry.register(PayEquityGuardianAgent())
_register_with_orchestration(pay_equity_agent)
