"""Central configuration for the TalentMind AI Platform.

All AI behaviour is driven by environment variables so the rest of the
application never hard-codes a provider, model or key. :class:`AISettings` is the
single source of truth consumed by the runner, the provider factory, the cache
and telemetry.

Environment variables (all optional — safe, offline defaults are provided):

    TALENTMIND_AI_PROVIDER      local | openai | claude | gemini | ollama   (default: local)
    TALENTMIND_AI_MODEL         model id override for the active provider
    TALENTMIND_AI_TEMPERATURE   float (default: 0.2)
    TALENTMIND_AI_MAX_TOKENS    int   (default: 1200)
    TALENTMIND_AI_TIMEOUT       seconds, float (default: 30)
    TALENTMIND_AI_MAX_RETRIES   int   (default: 2)
    TALENTMIND_AI_CACHE_ENABLED 1/0/true/false (default: true)
    TALENTMIND_AI_CACHE_DIR     path (default: data/ai_cache)
    TALENTMIND_AI_TELEMETRY_DIR path (default: logs)
    TALENTMIND_AI_STRICT        1/0 — if true, never fall back to the deterministic
                                composer on provider failure (default: false)

    OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY   provider credentials
    OLLAMA_HOST                 (default: http://localhost:11434)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict

# Default model per provider. Kept here (not in provider code) so ops can reason
# about the whole platform's model surface from one place.
_DEFAULT_MODELS: Dict[str, str] = {
    "local": "deterministic-composer-v1",
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-5",
    "gemini": "gemini-1.5-flash",
    "ollama": "llama3.1",
}

_TRUE = {"1", "true", "yes", "on"}


def _get_bool(name: str, default: bool) -> bool:
    """Read a boolean env var, tolerant of common truthy spellings."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


def _get_float(name: str, default: float) -> float:
    """Read a float env var, falling back to ``default`` on parse failure."""
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_int(name: str, default: int) -> int:
    """Read an int env var, falling back to ``default`` on parse failure."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AISettings:
    """Immutable, environment-derived AI platform configuration.

    Attributes:
        provider: Active provider key (``local`` by default — fully offline).
        model: Model id for the active provider.
        temperature: Sampling temperature for real providers.
        max_tokens: Max output tokens for real providers.
        timeout: Per-call timeout in seconds.
        max_retries: How many times the runner re-asks a provider for valid JSON.
        cache_enabled: Whether responses are read from / written to the cache.
        cache_dir: Directory for the file cache.
        telemetry_dir: Directory for telemetry logs.
        strict: If ``True``, provider failures raise instead of falling back to
            the deterministic composer.
    """

    provider: str = "local"
    model: str = "deterministic-composer-v1"
    temperature: float = 0.2
    max_tokens: int = 1200
    timeout: float = 30.0
    max_retries: int = 2
    cache_enabled: bool = True
    cache_dir: str = "data/ai_cache"
    telemetry_dir: str = "logs"
    strict: bool = False
    extra: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "AISettings":
        """Build settings from the process environment (with safe defaults)."""
        provider = os.environ.get("TALENTMIND_AI_PROVIDER", "local").strip().lower()
        if provider not in _DEFAULT_MODELS:
            provider = "local"
        model = os.environ.get("TALENTMIND_AI_MODEL") or _DEFAULT_MODELS[provider]

        return cls(
            provider=provider,
            model=model,
            temperature=_get_float("TALENTMIND_AI_TEMPERATURE", 0.2),
            max_tokens=_get_int("TALENTMIND_AI_MAX_TOKENS", 1200),
            timeout=_get_float("TALENTMIND_AI_TIMEOUT", 30.0),
            max_retries=_get_int("TALENTMIND_AI_MAX_RETRIES", 2),
            cache_enabled=_get_bool("TALENTMIND_AI_CACHE_ENABLED", True),
            cache_dir=os.environ.get("TALENTMIND_AI_CACHE_DIR", "data/ai_cache"),
            telemetry_dir=os.environ.get("TALENTMIND_AI_TELEMETRY_DIR", "logs"),
            strict=_get_bool("TALENTMIND_AI_STRICT", False),
        )


def default_model_for(provider: str) -> str:
    """Return the default model id for ``provider`` (``local`` if unknown)."""
    return _DEFAULT_MODELS.get(provider, _DEFAULT_MODELS["local"])
