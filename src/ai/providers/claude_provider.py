"""Anthropic Claude provider (SDK imported lazily).

Requires the ``anthropic`` package and ``ANTHROPIC_API_KEY``. Only touched when
the provider is actually selected and used.
"""

from __future__ import annotations

import importlib.util
from typing import Any

from src.ai.core.response import TokenUsage
from src.ai.providers._remote import RemoteProvider
from src.ai.providers.base import LLMMessage


class ClaudeProvider(RemoteProvider):
    """Messages-API provider for Anthropic Claude models."""

    key = "claude"
    env_key = "ANTHROPIC_API_KEY"

    def _sdk_available(self) -> bool:
        """Return ``True`` iff the ``anthropic`` SDK is importable."""
        return importlib.util.find_spec("anthropic") is not None

    def _client(self) -> Any:
        """Construct an Anthropic client (lazy import)."""
        import anthropic  # type: ignore

        return anthropic.Anthropic(api_key=self._api_key(), timeout=self.settings.timeout)

    def _complete(
        self, client: Any, messages: list[LLMMessage], json_mode: bool
    ) -> tuple[str, TokenUsage]:
        """Call messages.create and return ``(text, usage)``.

        Anthropic takes the system prompt separately, so system messages are
        merged into the top-level ``system`` argument.
        """
        system_parts = [m.content for m in messages if m.role == "system"]
        chat = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]

        response = client.messages.create(
            model=self.model,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            system="\n\n".join(system_parts) or None,
            messages=chat,
        )

        text = "".join(getattr(block, "text", "") for block in getattr(response, "content", []))
        usage = TokenUsage()
        if getattr(response, "usage", None):
            usage = TokenUsage(
                prompt_tokens=getattr(response.usage, "input_tokens", 0) or 0,
                completion_tokens=getattr(response.usage, "output_tokens", 0) or 0,
            )
        return text, usage
