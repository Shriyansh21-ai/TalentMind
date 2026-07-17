"""Telemetry logging for the AI Platform.

Records every AI run to a JSONL file (kept separate from application logs) and
keeps a small in-memory ring buffer for live UI display. Logging never raises —
observability must not be able to break a request.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import UTC, datetime

from src.ai.telemetry.models import TelemetryEvent

_RING_SIZE = 200


class TelemetryLogger:
    """Append-only JSONL telemetry sink with an in-memory tail."""

    def __init__(self, directory: str = "logs", filename: str = "ai_telemetry.jsonl") -> None:
        """Bind the logger to ``directory/filename`` (created lazily)."""
        self.directory = directory
        self.path = os.path.join(directory, filename)
        self._ring: deque[TelemetryEvent] = deque(maxlen=_RING_SIZE)

    def record(self, event: TelemetryEvent) -> None:
        """Persist ``event`` to disk and the in-memory ring (best-effort)."""
        if event.timestamp is None:
            event.timestamp = datetime.now(UTC).isoformat(timespec="seconds")
        self._ring.append(event)
        try:
            os.makedirs(self.directory, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except OSError:
            # Never let telemetry I/O break the request.
            pass

    def recent(self, limit: int = 50) -> list[TelemetryEvent]:
        """Return the most recent events (newest last), up to ``limit``."""
        events = list(self._ring)
        return events[-limit:]


# Process-wide default logger (directory can be overridden via settings when the
# runner constructs its own). Kept module-level so telemetry is trivially shared.
_default_logger: TelemetryLogger | None = None


def get_default_logger(directory: str = "logs") -> TelemetryLogger:
    """Return a shared :class:`TelemetryLogger`, creating it on first use."""
    global _default_logger
    if _default_logger is None or _default_logger.directory != directory:
        _default_logger = TelemetryLogger(directory=directory)
    return _default_logger
