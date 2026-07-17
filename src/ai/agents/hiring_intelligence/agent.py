"""HiringIntelligenceAgent — Workforce Hiring Intelligence (Phase 5 / M5).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` that produces the
:class:`WorkforceNarrative` from the aggregated cohort analytics the engine already
assembled. It provides strategic organizational intelligence — never candidate
ranking — and never fabricates analytics, trends, KPIs or forecasts (Module 15).

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

from src.ai.agents.hiring_intelligence.composer import compose_workforce_narrative
from src.ai.agents.hiring_intelligence.schemas import WorkforceNarrative
from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class HiringIntelligenceInput:
    """Typed input for the HiringIntelligenceAgent.

    ``analytics`` is the aggregated cohort analytics dict the engine already
    assembled — the agent recomputes nothing (Module 14).
    """

    cohort_size: int = 0
    data_available: bool = False
    analytics: dict[str, Any] = field(default_factory=dict)


def build_intelligence_evidence(payload: HiringIntelligenceInput) -> dict[str, Any]:
    """Pack the aggregated cohort analytics into the evidence dict."""
    analytics = dict(payload.analytics or {})
    analytics.setdefault("cohort_size", payload.cohort_size)
    analytics.setdefault("data_available", payload.data_available)
    return {
        "cohort_size": payload.cohort_size,
        "data_available": payload.data_available,
        "analytics": analytics,
    }


class HiringIntelligenceAgent(BaseAgent):
    """Narrates enterprise workforce analytics (strategic, never candidate ranking)."""

    metadata = AgentMetadata(
        name="hiring_intelligence",
        version="v1",
        title="Hiring Intelligence & Workforce Analytics",
        description=(
            "Aggregates the platform's existing hiring intelligence into strategic "
            "organizational analytics — hiring health, pipeline bottlenecks, team "
            "analytics, trends, executive KPIs, capacity, forecasts, benchmarks and "
            "optimization opportunities. Provides organizational intelligence only "
            "(never candidate ranking); marks unavailable metrics honestly and "
            "fabricates no enterprise statistics, trends, KPIs or forecasts."
        ),
        prompt_id="hiring_intelligence",
        prompt_version="v1",
        tags=["workforce", "analytics", "intelligence", "kpi", "trends", "executive", "hr"],
    )
    output_schema = WorkforceNarrative

    def build_messages(self, payload, loader, evidence: dict[str, Any]) -> list[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: HiringIntelligenceInput) -> dict[str, Any]:
        """Return the aggregated cohort analytics evidence for ``payload``."""
        return build_intelligence_evidence(payload)

    def prompt_values(
        self, payload: HiringIntelligenceInput, evidence: dict[str, Any]
    ) -> dict[str, str]:
        """Supply cohort-size + data-availability placeholders for the prompt."""
        analytics = evidence.get("analytics", {})
        health = next(
            (k for k in analytics.get("kpis", []) if k.get("name") == "Hiring Health Index"), {}
        )
        return {
            "cohort_size": str(payload.cohort_size),
            "hiring_health": str(health.get("label", "n/a")),
            "data_available": "yes"
            if payload.data_available
            else "no (analytics source not connected)",
        }

    def cache_dimensions(self, payload: HiringIntelligenceInput) -> tuple[str, str]:
        """Cache by cohort size (subject) + full analytics signature (scope)."""
        scope = json.dumps(build_intelligence_evidence(payload), sort_keys=True, default=str)
        return f"workforce_{payload.cohort_size}", scope


def _orchestration_payload_builder(task, context) -> HiringIntelligenceInput:
    """Build a :class:`HiringIntelligenceInput` from an orchestration task."""
    payload = task.payload or {}
    return HiringIntelligenceInput(
        cohort_size=int(payload.get("cohort_size", 0)),
        data_available=bool(payload.get("data_available", False)),
        analytics=payload.get("analytics", {}),
    )


def _register_with_orchestration(agent: HiringIntelligenceAgent) -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["hiring_intelligence", "workforce_analytics", "hiring_analytics"],
                payload_builder=_orchestration_payload_builder,
                name="hiring_intelligence",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(WorkforceNarrative.schema_name(), compose_workforce_narrative)
hiring_intelligence_agent = registry.register(HiringIntelligenceAgent())
_register_with_orchestration(hiring_intelligence_agent)
