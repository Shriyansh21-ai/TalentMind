"""Provider abstraction for the AI Platform.

The rest of the application depends only on :class:`BaseLLMProvider`; it never
imports a vendor SDK. Concrete providers import their SDK **lazily** (inside
methods / constructors) so importing this package — and booting the app — never
requires any provider library to be installed.

Contract (all providers implement):

    generate(messages)            -> AgentResponse   (free-form text)
    generate_json(messages, ...)  -> AgentResponse   (text is a JSON string)
    stream(messages)              -> Iterator[str]   (token/chunk stream)
    health_check()                -> bool            (usable right now?)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from src.ai.config.settings import AISettings
from src.ai.core.response import AgentResponse


@dataclass
class LLMMessage:
    """A single chat message.

    Attributes:
        role: ``"system"`` | ``"user"`` | ``"assistant"``.
        content: Message text.
    """

    role: str
    content: str


class BaseLLMProvider(ABC):
    """Abstract base every LLM provider implements.

    Attributes:
        key: Short provider identifier (``"openai"``, ``"local"``, ...).
    """

    key: str = "base"

    def __init__(self, settings: AISettings) -> None:
        """Store settings; concrete providers must not open connections here."""
        self.settings = settings

    # -- identity -----------------------------------------------------------

    @property
    def model(self) -> str:
        """Return the model id this provider will use."""
        return self.settings.model

    @property
    def is_deterministic(self) -> bool:
        """Return ``True`` for offline/deterministic providers (no network)."""
        return False

    # -- required capabilities ---------------------------------------------

    @abstractmethod
    def generate(self, messages: list[LLMMessage], **kwargs: Any) -> AgentResponse:
        """Generate free-form text for ``messages``."""

    @abstractmethod
    def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema: dict[str, Any],
        schema_name: str,
        evidence: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Generate a JSON object (returned as a JSON string in ``AgentResponse.text``).

        Args:
            messages: The rendered chat messages.
            schema: JSON schema the output must satisfy (used by real providers
                to instruct/validate the model).
            schema_name: Stable schema identifier (used by deterministic
                providers to select a composer).
            evidence: The structured facts backing the request. Real providers
                may ignore this (it is also embedded in ``messages``); the local
                deterministic provider composes its answer from it.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return ``True`` if the provider can be used right now (cheap check)."""

    # -- optional streaming (safe default) ---------------------------------

    def stream(self, messages: list[LLMMessage], **kwargs: Any) -> Iterator[str]:
        """Yield the response in chunks.

        Default implementation yields the full non-streaming result once, so every
        provider satisfies the streaming contract without bespoke code.
        """
        yield self.generate(messages, **kwargs).text
