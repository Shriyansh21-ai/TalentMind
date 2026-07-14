"""JSON-backed persistence for the Hiring Pipeline Engine.

The store serializes :class:`CandidatePipelineStatus` records to a single JSON
document (``data/pipeline_state.json`` by default). It is intentionally decoupled
from the existing lightweight ``src/recruiter/pipeline.py`` action store — that
module (the simple ``candidate_id -> status`` map used by the legacy card
buttons) is left completely untouched; this richer pipeline state lives in its
own file so there is zero risk of regressing the original workflow.

The store is a thin repository: it knows how to (de)serialize and where to read /
write, but contains no transition or validation logic (that lives in
``engine.py``).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Dict, Optional

from src.pipeline.models import (
    CandidatePipelineStatus,
    PipelineStage,
    Priority,
    StageEvent,
)

DEFAULT_STORE_PATH = "data/pipeline_state.json"


class PipelineStore:
    """Load / save the full pipeline state map keyed by ``candidate_id``.

    A single instance owns one JSON file. All reads go through :meth:`load` and
    all writes through :meth:`save`, so callers never touch the filesystem
    directly. The store creates the backing directory on first write and treats a
    missing / empty / corrupt file as an empty pipeline (never raising on read),
    which keeps the UI resilient on a fresh checkout.
    """

    def __init__(self, path: str = DEFAULT_STORE_PATH) -> None:
        """Bind the store to ``path`` (not read until :meth:`load`)."""
        self.path = path

    # -- serialization ------------------------------------------------------

    @staticmethod
    def _to_dict(status: CandidatePipelineStatus) -> dict:
        """Serialize one status record to a JSON-safe dict."""
        payload = asdict(status)
        payload["current_stage"] = status.current_stage.value
        payload["priority"] = status.priority.value
        return payload

    @staticmethod
    def _from_dict(data: dict) -> CandidatePipelineStatus:
        """Deserialize one status record, tolerating partial / legacy payloads."""
        history = [
            StageEvent(
                to_stage=event["to_stage"],
                timestamp=event.get("timestamp", ""),
                from_stage=event.get("from_stage"),
                actor=event.get("actor"),
                note=event.get("note"),
            )
            for event in data.get("stage_history", [])
        ]
        return CandidatePipelineStatus(
            candidate_id=data["candidate_id"],
            current_stage=PipelineStage.from_value(
                data.get("current_stage", PipelineStage.APPLIED.value)
            ),
            stage_history=history,
            status=data.get("status", "Active"),
            assigned_recruiter=data.get("assigned_recruiter"),
            priority=Priority(data.get("priority", Priority.MEDIUM.value)),
            last_updated=data.get("last_updated"),
            notes=list(data.get("notes", [])),
            tags=list(data.get("tags", [])),
        )

    # -- io -----------------------------------------------------------------

    def load(self) -> Dict[str, CandidatePipelineStatus]:
        """Return the full ``candidate_id -> status`` map (empty if unavailable)."""
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

        result: Dict[str, CandidatePipelineStatus] = {}
        for candidate_id, payload in raw.items():
            try:
                result[candidate_id] = self._from_dict(payload)
            except (KeyError, ValueError):
                # Skip individual corrupt records rather than failing the load.
                continue
        return result

    def save(self, states: Dict[str, CandidatePipelineStatus]) -> None:
        """Persist the full pipeline state map atomically-ish via write-replace."""
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        serializable = {
            candidate_id: self._to_dict(status)
            for candidate_id, status in states.items()
        }

        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(serializable, handle, indent=4)
        os.replace(tmp_path, self.path)

    def get(self, candidate_id: str) -> Optional[CandidatePipelineStatus]:
        """Return a single candidate's status, or ``None`` if not tracked yet."""
        return self.load().get(candidate_id)

    def put(self, status: CandidatePipelineStatus) -> None:
        """Upsert a single candidate's status, preserving all others."""
        states = self.load()
        states[status.candidate_id] = status
        self.save(states)
