"""Domain models for the Recruiter Copilot.

Pure data + enums, free of any UI or engine import so they can be shared by the
planner, controller, response builder and the UI without coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Intent(str, Enum):
    """Recruiter intents the copilot can handle."""

    SEARCH_CANDIDATE = "Search Candidate"
    COMPARE_CANDIDATES = "Compare Candidates"
    EXPLAIN_RANKING = "Explain Ranking"
    GENERATE_HIRING_SUMMARY = "Generate Hiring Summary"
    ANALYZE_CANDIDATE = "Analyze Candidate"
    GENERATE_INTERVIEW_PLAN = "Generate Interview Plan"
    PIPELINE_QUESTION = "Pipeline Question"
    DASHBOARD_QUESTION = "Dashboard Question"
    SKILL_SEARCH = "Skill Search"
    RECOMMENDATION_QUESTION = "Recommendation Question"
    RESUME_REVIEW = "Resume Review"
    JD_ANALYSIS = "JD Analysis"
    HIRING_COMMITTEE = "Hiring Committee"
    EXECUTIVE_REPORT = "Executive Report"
    INTERVIEW_STUDIO = "Interview Studio"
    COMPENSATION_GOVERNANCE = "Compensation Governance"
    PAY_EQUITY = "Pay Equity"
    HIRING_COMPLIANCE = "Hiring Compliance"
    HIRING_AUDIT = "Hiring Audit"
    HIRING_INTELLIGENCE = "Hiring Intelligence"
    GENERAL_HIRING_QUESTION = "General Hiring Question"


@dataclass
class Entities:
    """Structured entities extracted from a recruiter message.

    Attributes:
        candidate_ids: Explicit candidate ids referenced (e.g. ``CAND_0000001``).
        skills: Recognized skill keywords.
        query: The free-text search query (usually the message itself).
        top_k: Requested result count (parsed from "top N").
    """

    candidate_ids: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    query: str = ""
    top_k: int = 5


@dataclass
class IntentResult:
    """Result of intent classification.

    Attributes:
        intent: The detected :class:`Intent`.
        confidence: 0-100 confidence in the classification.
        entities: Extracted entities.
        scores: Per-intent match scores (for transparency / debugging).
    """

    intent: Intent
    confidence: float
    entities: Entities
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class CopilotPlan:
    """A plan of which tools to run for a request.

    Attributes:
        intent: The intent driving the plan.
        steps: Ordered ``[(tool_name, tool_input), ...]`` to execute.
        rationale: Human-readable reason for this tool selection.
    """

    intent: Intent
    steps: List[tuple] = field(default_factory=list)
    rationale: str = ""
    focus_candidate: Optional[str] = None
    comparison_ids: List[str] = field(default_factory=list)

    @property
    def tool_names(self) -> List[str]:
        """Return the tool names in the plan."""
        return [name for name, _ in self.steps]


@dataclass
class CopilotAction:
    """A recruiter action offered alongside an answer.

    Attributes:
        type: Action type key (e.g. ``move_to_shortlist``).
        label: Button label shown to the recruiter.
        params: Parameters the UI needs to execute the action.
    """

    type: str
    label: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """A single conversation message."""

    role: str  # "user" | "assistant"
    content: str


@dataclass
class CopilotTurn:
    """The full result of one copilot exchange.

    Attributes:
        message: The recruiter's message.
        answer: The recruiter-quality narrative answer.
        intent: The detected intent.
        reasoning_summary: Short summary of how the answer was derived.
        confidence_note: Uncertainty / confidence statement.
        tools_used: Compact per-tool metadata (for tool-visibility cards).
        evidence_sources: Distinct engines that produced the evidence.
        follow_ups: Suggested follow-up questions (deterministic).
        actions: Suggested recruiter actions.
        provider: AI provider used for narration.
        model: AI model used.
        cache_hit: Whether the AI narration came from cache.
        latency_ms: Total turn latency.
        status: ``ok`` | ``failed``.
    """

    message: str
    answer: str
    intent: Intent
    reasoning_summary: str = ""
    confidence_note: str = ""
    tools_used: List[Dict[str, Any]] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    follow_ups: List[str] = field(default_factory=list)
    actions: List[CopilotAction] = field(default_factory=list)
    provider: str = "local"
    model: str = ""
    cache_hit: bool = False
    latency_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None
