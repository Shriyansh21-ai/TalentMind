"""Telemetry event model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TelemetryEvent:
    """A single AI-run telemetry record.

    Attributes:
        request_id: Correlation id for the run.
        agent: Agent name.
        agent_version: Agent version.
        provider: Provider actually used.
        model: Model actually used.
        status: Run outcome (``success`` / ``cached`` / ``fallback`` / ``failed``).
        latency_ms: Total wall-clock time.
        prompt_tokens / completion_tokens: Token accounting.
        cache_hit: Whether the response came from cache.
        retries: Provider retries consumed.
        subject_id: Primary entity id (e.g. candidate id).
        timestamp: ISO-8601 event time (injected by the logger).
        warnings: Non-fatal advisories.
        error: Error message when failed.
    """

    request_id: str
    agent: str
    agent_version: str
    provider: str
    model: str
    status: str
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit: bool = False
    retries: int = 0
    subject_id: str = "global"
    timestamp: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict of the event."""
        return asdict(self)
