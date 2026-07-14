"""Provider factory — the only place that maps a provider key to a class.

Encapsulates provider selection so callers ask for "the configured provider" and
never import a concrete provider. If the configured provider is not healthy (no
SDK / no key) and the platform is not in strict mode, the factory transparently
falls back to the always-available :class:`LocalHeuristicProvider`.
"""

from __future__ import annotations

from typing import Dict, Tuple, Type

from src.ai.config.settings import AISettings
from src.ai.core.exceptions import ProviderUnavailableError
from src.ai.providers.base import BaseLLMProvider
from src.ai.providers.local import LocalHeuristicProvider
from src.ai.providers.openai_provider import OpenAIProvider
from src.ai.providers.claude_provider import ClaudeProvider
from src.ai.providers.gemini_provider import GeminiProvider
from src.ai.providers.ollama_provider import OllamaProvider

_REGISTRY: Dict[str, Type[BaseLLMProvider]] = {
    "local": LocalHeuristicProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def register_provider(key: str, provider_cls: Type[BaseLLMProvider]) -> None:
    """Register a custom provider class under ``key`` (extension point)."""
    _REGISTRY[key] = provider_cls


def build_provider(key: str, settings: AISettings) -> BaseLLMProvider:
    """Instantiate the provider registered under ``key``.

    Raises:
        ProviderUnavailableError: If ``key`` is unknown.
    """
    provider_cls = _REGISTRY.get(key)
    if provider_cls is None:
        raise ProviderUnavailableError(f"Unknown provider {key!r}.")
    return provider_cls(settings)


def get_provider(settings: AISettings) -> Tuple[BaseLLMProvider, list]:
    """Return ``(provider, warnings)`` for the configured provider.

    If the configured provider is unhealthy and the platform is not strict, a
    :class:`LocalHeuristicProvider` is returned instead and a warning is recorded
    so callers/telemetry can surface the substitution.

    Args:
        settings: Resolved platform settings.

    Returns:
        A tuple of the chosen provider and a list of human-readable warnings.
    """
    warnings: list = []
    provider = build_provider(settings.provider, settings)

    if provider.is_deterministic:
        return provider, warnings

    if provider.health_check():
        return provider, warnings

    if settings.strict:
        raise ProviderUnavailableError(
            f"Configured provider {settings.provider!r} is unavailable and "
            "strict mode is enabled."
        )

    warnings.append(
        f"Provider {settings.provider!r} unavailable; using deterministic "
        "local provider instead."
    )
    return LocalHeuristicProvider(settings), warnings


def available_providers(settings: AISettings) -> Dict[str, bool]:
    """Return ``{provider_key: healthy}`` for every registered provider."""
    status: Dict[str, bool] = {}
    for key, provider_cls in _REGISTRY.items():
        try:
            status[key] = provider_cls(settings).health_check()
        except Exception:
            status[key] = False
    return status
