"""Executive Chair (Module 6).

The Chair is a :class:`BaseAgent` on the AI Platform: it consumes the committee's
*structured deliberation* (opinions + consensus + conflicts + confidence) and
produces a :class:`CommitteeDecision`. Offline it uses a deterministic composer
(the decision is a pure function of the deliberation, so it cannot fabricate);
with a real provider the same deliberation is embedded in the prompt.

The recommendation itself comes from the evidence-weighted consensus — the Chair
narrates and justifies it, it does not re-decide by fiat.
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

from src.ai.committee.schemas import CommitteeDecision

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
_prompt_loader = PromptLoader(_PROMPTS_DIR)


@dataclass
class ChairInput:
    """Typed input for the Chair: the full structured deliberation."""

    candidate_overview: Dict[str, Any] = field(default_factory=dict)
    resume_summary: str = ""
    jd_summary: str = ""
    mode: str = "balanced"
    opinions: List[Dict[str, Any]] = field(default_factory=list)
    consensus: Dict[str, Any] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    confidence: Dict[str, Any] = field(default_factory=dict)
    discussion: Dict[str, Any] = field(default_factory=dict)

    def as_evidence(self) -> Dict[str, Any]:
        """Return the deliberation as the agent's evidence dict."""
        return {
            "candidate_overview": self.candidate_overview,
            "resume_summary": self.resume_summary,
            "jd_summary": self.jd_summary,
            "mode": self.mode,
            "opinions": self.opinions,
            "consensus": self.consensus,
            "conflicts": self.conflicts,
            "confidence": self.confidence,
            "discussion": self.discussion,
        }


# ---------------------------------------------------------------------------
# Deterministic composer (offline reasoning)
# ---------------------------------------------------------------------------


def _opinions_by_role(evidence: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Index opinions by role for justification lookups."""
    return {o.get("role", ""): o for o in evidence.get("opinions", [])}


def compose_committee_decision(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministically compose a :class:`CommitteeDecision` from deliberation."""
    ev = evidence or {}
    consensus = ev.get("consensus", {})
    confidence = ev.get("confidence", {})
    overview = ev.get("candidate_overview", {})
    by_role = _opinions_by_role(ev)

    recommendation = consensus.get("recommendation", "Hold")
    level = consensus.get("level", "No Consensus")
    title = overview.get("title") or "the candidate"

    executive_summary = (
        f"The AI Hiring Committee reached a **{level}** and recommends "
        f"**{recommendation}** for {title}. "
        f"{consensus.get('reasoning', '')} "
        f"Overall decision confidence: {confidence.get('overall', 0):.0f}/100."
    )

    analyst = by_role.get("hiring_analyst", {})
    jd = by_role.get("jd_expert", {})
    business_justification = (
        f"Hiring Analyst: {analyst.get('opinion', 'n/a')} "
        f"JD context: {jd.get('opinion', 'role context not provided.')}"
    ).strip()

    tech = by_role.get("technical_hiring_manager", {})
    resume = by_role.get("resume_expert", {})
    technical_justification = (
        f"Technical Hiring Manager: {tech.get('opinion', 'n/a')} "
        f"Resume evidence: {resume.get('opinion', 'n/a')}"
    ).strip()

    risk = by_role.get("risk_officer", {})
    hiring_risks = list(risk.get("concerns", []))
    for conflict in ev.get("conflicts", []):
        hiring_risks.append(
            f"Unresolved tension: {conflict.get('member_a')} vs {conflict.get('member_b')} — "
            f"{conflict.get('resolution_strategy', '')}"
        )

    interview = by_role.get("interview_lead", {})
    interview_priorities = list(interview.get("strengths", []))[:4] or list(interview.get("concerns", []))[:4]

    remaining_unknowns: List[str] = list(ev.get("discussion", {}).get("missing_evidence", []))
    unknown_expl = confidence.get("explanations", {}).get("unknown_risk")
    if unknown_expl:
        remaining_unknowns.append(unknown_expl)

    follow_up_actions = _follow_ups(recommendation, ev)

    confidence_note = (
        f"Decision confidence {confidence.get('overall', 0):.0f}/100 — "
        f"{confidence.get('explanations', {}).get('consensus_strength', '')} "
        f"{confidence.get('explanations', {}).get('evidence_coverage', '')} "
        "Confidence is derived from evidence coverage, consensus strength, member "
        "confidence spread, decision stability and unknown risk."
    )

    return {
        "executive_summary": executive_summary,
        "recommendation": recommendation,
        "business_justification": business_justification or "No business justification evidence available.",
        "technical_justification": technical_justification or "No technical justification evidence available.",
        "hiring_risks": hiring_risks[:6],
        "interview_priorities": interview_priorities,
        "remaining_unknowns": remaining_unknowns[:6],
        "follow_up_actions": follow_up_actions,
        "confidence_note": confidence_note,
    }


def _follow_ups(recommendation: str, ev: Dict[str, Any]) -> List[str]:
    """Derive concrete follow-up actions from the recommendation + gaps."""
    actions: List[str] = []
    low = recommendation.lower()
    if "hire" in low and "no" not in low:
        actions.append("Advance to interview; confirm the committee's validation items.")
    elif "hold" in low:
        actions.append("Gather the missing evidence before deciding (see remaining unknowns).")
    else:
        actions.append("Do not advance; document the blocking concerns for the requisition.")
    if ev.get("conflicts"):
        actions.append("Resolve the flagged disagreements with targeted interview questions.")
    if not ev.get("jd_summary") or ev.get("jd_summary", "").startswith("No job"):
        actions.append("Attach the job description to sharpen role-fit reasoning.")
    return actions


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class CommitteeChairAgent(BaseAgent):
    """Synthesizes the committee deliberation into an executive decision."""

    metadata = AgentMetadata(
        name="committee_chair",
        version="v1",
        title="Committee Chair",
        description=(
            "Chairs the AI Hiring Committee: narrates and justifies the "
            "evidence-weighted consensus into an executive hiring decision. Never "
            "re-decides or fabricates — grounded entirely in the deliberation."
        ),
        prompt_id="committee_chair",
        prompt_version="v1",
        tags=["committee", "chair", "executive", "decision"],
    )
    output_schema = CommitteeDecision

    def build_messages(self, payload, loader, evidence: Dict[str, Any]) -> List[LLMMessage]:
        """Render prompts from the committee's own ``prompts/`` directory."""
        return super().build_messages(payload, _prompt_loader, evidence)

    def build_evidence(self, payload: ChairInput) -> Dict[str, Any]:
        """Return the deliberation as evidence."""
        return payload.as_evidence()

    def prompt_values(self, payload: ChairInput, evidence: Dict[str, Any]) -> Dict[str, str]:
        """Supply candidate + consensus placeholders for the prompt."""
        return {
            "candidate_id": payload.candidate_overview.get("candidate_id", "unknown"),
            "consensus_recommendation": payload.consensus.get("recommendation", "Hold"),
        }

    def cache_dimensions(self, payload: ChairInput) -> Tuple[str, str]:
        """Cache by candidate id + a deliberation signature."""
        cid = payload.candidate_overview.get("candidate_id", "committee")
        signature = json.dumps(payload.as_evidence(), sort_keys=True, default=str)
        return cid, signature


register_composer(CommitteeDecision.schema_name(), compose_committee_decision)
committee_chair_agent = registry.register(CommitteeChairAgent())
