"""CompensationGovernanceAgent — Enterprise Compensation Governance (Phase 5 / M1).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
:class:`CompensationNarrative` from the aggregated intelligence TalentMind already
computed plus the candidate's own stated expectation. It does **not predict
salaries** — it explains, justifies and governs a compensation recommendation so
HR, Finance, Legal and executives can approve it (Module 16). It adds no ranking
and no hiring logic.

Everything infrastructural (prompt rendering, provider calls, retries,
validation, safety, caching, telemetry, deterministic fallback) comes for free
from :class:`AgentRunner`; this module only supplies the evidence packing + the
identity.

On import it auto-registers with:
  * the AI Platform agent registry,
  * the deterministic composer registry (offline reasoning),
  * the Multi-Agent Orchestration registry (via a ``RunnerAgent`` adapter),
so the orchestrator and the Recruiter Copilot discover it with no manual wiring.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from src.ai.agents.compensation.composer import compose_compensation_narrative
from src.ai.agents.compensation.schemas import CompensationNarrative
from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

# Prompts co-locate with the agent; a dedicated loader points at this package's
# ``prompts/`` dir, leaving the shared prompt library untouched.
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class CompensationInput:
    """Typed input for the CompensationGovernanceAgent.

    Every field is an existing engine/agent output or the candidate's own stated
    expectation, already normalized to a dict by the engine — the agent recomputes
    nothing. All are optional so the agent degrades gracefully when a source is
    missing (Module 16).
    """

    candidate_id: str = ""
    candidate_overview: dict[str, Any] = field(default_factory=dict)
    candidate_comp: dict[str, Any] = field(default_factory=dict)
    resume: dict[str, Any] = field(default_factory=dict)
    jd: dict[str, Any] = field(default_factory=dict)
    committee: dict[str, Any] = field(default_factory=dict)
    intelligence: dict[str, Any] = field(default_factory=dict)
    timeline: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    recommendation: dict[str, Any] = field(default_factory=dict)
    interview: dict[str, Any] = field(default_factory=dict)
    # Heuristics the engine computes before narration (so the AI can cite them).
    recommended_range: dict[str, Any] = field(default_factory=dict)
    market_position: str = ""
    hire_type: str = ""


def build_compensation_evidence(payload: CompensationInput) -> dict[str, Any]:
    """Pack the pre-gathered structured outputs into the evidence dict.

    This is the sole factual input to the narrative: existing engine/agent outputs
    + the candidate's stated expectation + the engine's own heuristic range.
    Nothing the AI may fabricate (Module 16).
    """
    return {
        "candidate_overview": payload.candidate_overview or {},
        "candidate_comp": payload.candidate_comp or {},
        "resume": payload.resume or {},
        "jd": payload.jd or {},
        "committee": payload.committee or {},
        "intelligence": payload.intelligence or {},
        "timeline": payload.timeline or {},
        "risk": payload.risk or {},
        "recommendation": payload.recommendation or {},
        "interview": payload.interview or {},
        "recommended_range": payload.recommended_range or {},
        "market_position": payload.market_position,
        "hire_type": payload.hire_type,
    }


class CompensationGovernanceAgent(BaseAgent):
    """Explains, justifies and governs a compensation recommendation (never predicts)."""

    metadata = AgentMetadata(
        name="compensation_governance",
        version="v1",
        title="Compensation Governance",
        description=(
            "Explains, justifies, documents and governs a compensation "
            "recommendation using evidence from the existing AI ecosystem — "
            "resume, JD, candidate intelligence, timeline, risk, interview, "
            "committee and recommendation. Produces defensible ranges (never a "
            "fixed salary), an offer-justification audit trail, governance checks, "
            "market position, offer scenarios, negotiation strategy, budget "
            "assessment, internal-equity readiness and a transparency audit trail. "
            "Consumes existing outputs only; fabricates no salary or market data."
        ),
        prompt_id="compensation",
        prompt_version="v1",
        tags=["compensation", "governance", "transparency", "audit", "finance", "hr"],
    )
    output_schema = CompensationNarrative

    def build_messages(self, payload, loader, evidence: dict[str, Any]) -> list[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: CompensationInput) -> dict[str, Any]:
        """Return the aggregated compensation evidence for ``payload``."""
        return build_compensation_evidence(payload)

    def prompt_values(self, payload: CompensationInput, evidence: dict[str, Any]) -> dict[str, str]:
        """Supply candidate id + heuristic-range placeholders for the prompt."""
        rr = payload.recommended_range or {}
        if rr:
            range_str = (
                f"{rr.get('currency', 'INR')} {rr.get('minimum', 0)}-{rr.get('maximum', 0)} "
                f"{rr.get('unit', 'LPA')} (target {rr.get('target', 0)})"
            )
        else:
            range_str = "not yet computed"
        return {
            "candidate_id": payload.candidate_id or "unknown",
            "recommended_range": range_str,
            "market_position": payload.market_position or "Market Competitive",
            "hire_type": payload.hire_type or "Growth Hire",
        }

    def cache_dimensions(self, payload: CompensationInput) -> tuple[str, str]:
        """Cache by candidate id (subject) + full evidence signature (scope)."""
        scope = json.dumps(build_compensation_evidence(payload), sort_keys=True, default=str)
        return payload.candidate_id or "compensation", scope


def _orchestration_payload_builder(task, context) -> CompensationInput:
    """Build a :class:`CompensationInput` from an orchestration task + context."""
    payload = task.payload or {}
    overview = payload.get("candidate_overview") or {}
    if not overview and context is not None:
        candidate = getattr(context, "candidate", None)
        if candidate is not None:
            profile = getattr(candidate, "profile", None)
            overview = {
                "candidate_id": getattr(candidate, "candidate_id", ""),
                "title": getattr(profile, "current_title", ""),
                "company": getattr(profile, "current_company", ""),
                "years_of_experience": getattr(profile, "years_of_experience", 0.0),
                "location": getattr(profile, "location", ""),
            }
    return CompensationInput(
        candidate_id=str(
            payload.get("candidate_id", "") or overview.get("candidate_id", "") or "compensation"
        ),
        candidate_overview=overview,
        candidate_comp=payload.get("candidate_comp", {}),
        resume=payload.get("resume", {}),
        jd=payload.get("jd", {}),
        committee=payload.get("committee", {}),
        intelligence=payload.get("intelligence", {}),
        timeline=payload.get("timeline", {}),
        risk=payload.get("risk", {}),
        recommendation=payload.get("recommendation", {}),
        interview=payload.get("interview", {}),
        recommended_range=payload.get("recommended_range", {}),
        market_position=payload.get("market_position", ""),
        hire_type=payload.get("hire_type", ""),
    )


def _register_with_orchestration(agent: CompensationGovernanceAgent) -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["compensation_governance", "compensation", "offer_justification"],
                payload_builder=_orchestration_payload_builder,
                name="compensation_governance",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(CompensationNarrative.schema_name(), compose_compensation_narrative)
compensation_agent = registry.register(CompensationGovernanceAgent())
_register_with_orchestration(compensation_agent)
