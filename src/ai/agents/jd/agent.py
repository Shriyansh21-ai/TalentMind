"""JDAnalystAgent — enterprise job-description intelligence (Modules 1-12, 16, 17).

A specialized :class:`~src.ai.core.base_agent.BaseAgent` built entirely on the
existing AI Platform: prompt loader, provider layer, cache, telemetry, safety and
structured output all come for free from :class:`AgentRunner`. This module only
adds *intelligence* — the deterministic JD analysis pipeline
(extractors → metrics → validators → report → composer) — never infrastructure.

On import it auto-registers with:
  * the AI Platform agent registry,
  * the deterministic composer registry (offline reasoning),
  * the Multi-Agent Orchestration registry (via a ``RunnerAgent`` adapter),
so the orchestrator and the Recruiter Copilot discover it with no manual wiring.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

from src.ai.agents.jd import extractors, validators
from src.ai.agents.jd import metrics as metrics_mod
from src.ai.agents.jd.composer import compose_jd_analysis
from src.ai.agents.jd.schemas import JDAnalysis
from src.ai.core.base_agent import BaseAgent
from src.ai.core.metadata import AgentMetadata
from src.ai.core.registry import registry
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.providers.composers import register_composer

# The agent's prompts live with the agent. A dedicated loader points at this
# package's ``prompts/`` dir; the shared prompt library is left untouched.
_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class JDAnalystInput:
    """Typed input for the JDAnalystAgent.

    Attributes:
        jd_text: The raw Job Description text (the sole factual input).
        jd_id: Stable id used for caching + telemetry (defaults to a text hash).
        title: Optional explicit job title (else inferred from the first line).
    """

    jd_text: str = ""
    jd_id: str = ""
    title: str = ""


def build_jd_evidence(payload: JDAnalystInput) -> dict[str, Any]:
    """Run the deterministic pipeline and return the evidence dict.

    This is the sole factual input to the analysis: parsed document + computed
    metrics + evidence-backed risk findings + offline market estimates. It
    contains nothing the AI is allowed to invent (Module 17).
    """
    doc = extractors.extract(payload.jd_text, jd_id=payload.jd_id, title=payload.title)
    metrics = metrics_mod.compute_metrics(doc)
    risks = validators.detect_risks(doc, metrics)
    return {
        "document": doc.to_dict(),
        "text_blob": doc.all_text(),
        "metrics": metrics.to_dict(),
        "risks": [r.to_dict() for r in risks],
        "risk_level": validators.risk_level(risks),
        "positive_signals": validators.positive_signals(doc, metrics),
        "market_estimates": metrics_mod.market_estimates(doc, metrics),
    }


class JDAnalystAgent(BaseAgent):
    """Understands a JD's role, intent, quality and risk like a hiring manager."""

    metadata = AgentMetadata(
        name="jd_analyst",
        version="v1",
        title="JD Analyst",
        description=(
            "Enterprise job-description intelligence: role level, technical shape, "
            "hiring intent, organization context, requirement hierarchy, market "
            "posture, quality and evidence-based risks — JD quality only, never "
            "candidate ranking."
        ),
        prompt_id="jd_analyst",
        prompt_version="v1",
        tags=["jd", "job-description", "hiring-intent", "role-analysis", "market"],
    )
    output_schema = JDAnalysis

    def build_messages(self, payload, loader, evidence: dict[str, Any]) -> list[LLMMessage]:
        """Render prompts from the agent's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: JDAnalystInput) -> dict[str, Any]:
        """Return the deterministic JD evidence for ``payload``."""
        return build_jd_evidence(payload)

    def prompt_values(self, payload: JDAnalystInput, evidence: dict[str, Any]) -> dict[str, str]:
        """Supply the JD title + id placeholders for the prompt."""
        doc = evidence.get("document", {})
        return {
            "jd_id": payload.jd_id or _jd_hash(payload.jd_text),
            "jd_title": doc.get("title") or payload.title or "(untitled role)",
        }

    def cache_dimensions(self, payload: JDAnalystInput) -> tuple[str, str]:
        """Cache by JD id (subject) + a JD-text hash (scope) — Module 16."""
        return (payload.jd_id or "jd"), _jd_hash(payload.jd_text)


def _jd_hash(jd_text: str) -> str:
    """Return a stable content hash of the JD text (cache scope)."""
    return hashlib.sha256((jd_text or "").strip().lower().encode("utf-8")).hexdigest()[:24]


def _orchestration_payload_builder(task, context) -> JDAnalystInput:
    """Build a :class:`JDAnalystInput` from an orchestration task + context."""
    payload = task.payload or {}
    jd_text = payload.get("jd_text") or (getattr(context, "jd", "") if context is not None else "")
    return JDAnalystInput(
        jd_text=jd_text,
        jd_id=str(payload.get("jd_id", "") or ""),
        title=payload.get("title", ""),
    )


def _register_with_orchestration(agent: JDAnalystAgent) -> None:
    """Register the agent with the Multi-Agent Orchestration platform (best-effort)."""
    try:
        from src.ai.orchestration.adapters import RunnerAgent
        from src.ai.orchestration.registry.agent_registry import orchestration_registry

        orchestration_registry.register(
            RunnerAgent(
                agent,
                capabilities=["jd_analysis", "jd_review"],
                payload_builder=_orchestration_payload_builder,
                name="jd_analyst",
            )
        )
    except Exception:  # orchestration optional; never block agent registration
        pass


# ---------------------------------------------------------------------------
# Auto-registration (import side effects — the platform discovers the agent)
# ---------------------------------------------------------------------------

register_composer(JDAnalysis.schema_name(), compose_jd_analysis)
jd_analyst_agent = registry.register(JDAnalystAgent())
_register_with_orchestration(jd_analyst_agent)
