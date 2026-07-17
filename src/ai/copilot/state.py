"""Conversation state for the Recruiter Copilot.

Holds the "working set" a recruiter is operating on so follow-up messages can be
resolved contextually ("compare them", "analyze that candidate"). Kept as a plain
dataclass so it is trivial to serialize for future durable memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationState:
    """Mutable per-session working context.

    Attributes:
        current_candidate: The candidate currently in focus.
        current_comparison: Candidate ids in the active comparison set.
        current_jd: The job description in effect for JD-dependent tools.
        current_pipeline_candidate: Candidate referenced in pipeline actions.
        current_filters: Active dashboard/search filters.
        last_search_results: Candidate ids returned by the most recent search
            (lets "compare the top two" resolve without explicit ids).
    """

    current_candidate: str | None = None
    current_comparison: list[str] = field(default_factory=list)
    current_jd: str = ""
    current_pipeline_candidate: str | None = None
    current_filters: dict[str, object] = field(default_factory=dict)
    last_search_results: list[str] = field(default_factory=list)

    def focus_candidate(self, candidate_id: str) -> None:
        """Set the in-focus candidate."""
        if candidate_id:
            self.current_candidate = candidate_id

    def set_comparison(self, candidate_ids: list[str]) -> None:
        """Set the active comparison set (deduplicated, order-preserving)."""
        seen: list[str] = []
        for cid in candidate_ids:
            if cid and cid not in seen:
                seen.append(cid)
        self.current_comparison = seen

    def record_search(self, candidate_ids: list[str]) -> None:
        """Record the ids returned by the latest search."""
        self.last_search_results = list(candidate_ids)
