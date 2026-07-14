"""Local, deterministic, offline provider.

The default provider. It never touches the network and never invents anything:
``generate_json`` looks up the composer registered for the requested schema and
applies it to the structured evidence. This guarantees the AI Platform works out
of the box (no keys, no SDKs) and is the safety backstop when a real provider is
unavailable or misbehaves.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.ai.config.settings import AISettings
from src.ai.core.response import AgentResponse, TokenUsage
from src.ai.core.exceptions import ProviderUnavailableError
from src.ai.providers.base import BaseLLMProvider, LLMMessage
from src.ai.providers.composers import get_composer


class LocalHeuristicProvider(BaseLLMProvider):
    """Deterministic provider backed by the composer registry."""

    key = "local"

    def __init__(self, settings: AISettings) -> None:
        super().__init__(settings)

    @property
    def is_deterministic(self) -> bool:
        """This provider is fully deterministic and offline."""
        return True

    def generate(self, messages: List[LLMMessage], **kwargs: Any) -> AgentResponse:
        """Return the concatenated user content (no model call).

        Free-form generation has no deterministic analogue, so this simply echoes
        the last user message — useful for smoke tests and streaming defaults.
        """
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"), ""
        )
        return AgentResponse(
            text=last_user,
            provider=self.key,
            model=self.model,
            latency_ms=0.0,
            usage=TokenUsage(),
        )

    def generate_json(
        self,
        messages: List[LLMMessage],
        *,
        schema: Dict[str, Any],
        schema_name: str,
        evidence: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Compose a schema-shaped JSON response deterministically from evidence."""
        composer = get_composer(schema_name)
        if composer is None:
            raise ProviderUnavailableError(
                f"No deterministic composer registered for schema {schema_name!r}."
            )
        data = composer(evidence or {})
        return AgentResponse(
            text=json.dumps(data, ensure_ascii=False),
            provider=self.key,
            model=self.model,
            latency_ms=0.0,
            usage=TokenUsage(),
        )

    def health_check(self) -> bool:
        """The local provider is always available."""
        return True
