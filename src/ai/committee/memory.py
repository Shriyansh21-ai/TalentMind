"""Committee memory (Module 7).

Reuses the orchestration platform's memory interface
(:class:`InMemoryOrchestrationMemory`) — no new memory infrastructure. Stores
each meeting's individual opinions, consensus, disagreements, evidence and a
meeting-history index so the copilot can answer follow-up questions
("what did the committee disagree on?").
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.ai.orchestration.memory.memory import (
    InMemoryOrchestrationMemory,
    OrchestrationMemory,
)


class CommitteeMemory:
    """A thin, meeting-scoped facade over the orchestration memory."""

    def __init__(self, backend: Optional[OrchestrationMemory] = None) -> None:
        """Bind to an orchestration memory backend (in-process by default)."""
        self.backend = backend or InMemoryOrchestrationMemory()
        self._meetings: List[str] = []

    def remember_meeting(self, meeting_id: str, report_dict: Dict[str, Any]) -> None:
        """Persist a completed meeting's full report + indexed facets."""
        self.backend.remember(meeting_id, "report", report_dict)
        self.backend.remember(meeting_id, "opinions", report_dict.get("opinions", []))
        self.backend.remember(meeting_id, "consensus", report_dict.get("consensus", {}))
        self.backend.remember(meeting_id, "conflicts", report_dict.get("conflicts", []))
        self.backend.remember(meeting_id, "decision", report_dict.get("decision", {}))
        self.backend.append(
            "committee_history",
            {
                "meeting_id": meeting_id,
                "candidate_id": report_dict.get("candidate_id"),
                "recommendation": report_dict.get("consensus", {}).get("recommendation"),
                "consensus": report_dict.get("consensus", {}).get("level"),
            },
        )
        if meeting_id not in self._meetings:
            self._meetings.append(meeting_id)

    def recall_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """Return a stored meeting report (or empty dict)."""
        return self.backend.recall(meeting_id, "report", {})

    def facet(self, meeting_id: str, key: str) -> Any:
        """Return a stored facet (opinions / consensus / conflicts / decision)."""
        return self.backend.recall(meeting_id, key)

    def latest_for(self, candidate_id: str) -> Dict[str, Any]:
        """Return the most recent meeting report for a candidate (or empty)."""
        for entry in reversed(self.backend.trace("committee_history")):
            if entry.get("candidate_id") == candidate_id:
                return self.recall_meeting(entry["meeting_id"])
        return {}

    def history(self) -> List[Dict[str, Any]]:
        """Return the ordered meeting-history index."""
        return self.backend.trace("committee_history")
