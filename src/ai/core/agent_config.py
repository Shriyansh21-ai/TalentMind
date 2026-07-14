"""Per-run agent configuration.

Separated from :class:`AISettings` (which is process/environment level) so a
single call site can override behaviour for one run (e.g. force a refresh, or
disable the deterministic fallback) without mutating global settings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Per-invocation knobs for :class:`AgentRunner.run`.

    Attributes:
        use_cache: Read from / write to the response cache for this run.
        force_refresh: Ignore any cached value and recompute (still writes back).
        allow_fallback: Permit the deterministic composer fallback if the
            configured provider fails or is unavailable.
        max_retries: Optional override of ``AISettings.max_retries`` for this run.
    """

    use_cache: bool = True
    force_refresh: bool = False
    allow_fallback: bool = True
    max_retries: int | None = None
