"""Standardized agent response and result types.

Two levels of standardization:

* :class:`AgentResponse` wraps a *provider* call — raw text/json plus usage and
  timing. It is an internal, provider-agnostic envelope.
* :class:`AgentResult` is the *public* result of running an agent — a validated,
  schema-typed payload plus telemetry and status. This is the only thing the UI
  and services ever consume; no raw LLM output crosses this boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(str, Enum):
    """Outcome of an agent run."""

    SUCCESS = "success"          # produced by the configured provider
    CACHED = "cached"            # served from cache
    FALLBACK = "fallback"        # deterministic composer used (provider skipped/failed)
    FAILED = "failed"            # no usable result produced


@dataclass
class TokenUsage:
    """Token accounting for a provider call (zeros for offline providers)."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Return total tokens used."""
        return self.prompt_tokens + self.completion_tokens


@dataclass
class AgentResponse:
    """Provider-agnostic envelope for a single provider generation.

    Attributes:
        text: Raw text output (may be a JSON string for ``generate_json``).
        provider: Provider key that produced it.
        model: Model id used.
        latency_ms: Wall-clock latency of the provider call.
        usage: Token accounting.
        raw: Optional provider-native raw payload (debugging only).
    """

    text: str
    provider: str
    model: str
    latency_ms: float = 0.0
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: Optional[Any] = None


@dataclass
class AgentResult:
    """Public, standardized result of an agent run.

    Attributes:
        status: :class:`AgentStatus` outcome.
        agent: Agent name.
        agent_version: Agent version that produced this result.
        provider: Provider actually used (``"local"`` for deterministic).
        model: Model actually used.
        data: Validated, schema-typed payload (``None`` only when ``FAILED``).
        cache_hit: Whether the result came from cache.
        retries: How many provider retries were consumed.
        latency_ms: Total wall-clock time for the run.
        usage: Aggregate token usage.
        warnings: Non-fatal notes (safety softening, fallback reasons, ...).
        error: Error message when ``status == FAILED``.
    """

    status: AgentStatus
    agent: str
    agent_version: str
    provider: str
    model: str
    data: Optional[Any] = None
    cache_hit: bool = False
    retries: int = 0
    latency_ms: float = 0.0
    usage: TokenUsage = field(default_factory=TokenUsage)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """Return ``True`` when a usable payload is present."""
        return self.status != AgentStatus.FAILED and self.data is not None
