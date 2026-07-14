"""OpenAI provider (SDK imported lazily).

Requires the ``openai`` package and ``OPENAI_API_KEY``. Neither is needed to
import this module or boot the app — both are only touched when the provider is
actually selected and used.
"""

from __future__ import annotations

import importlib.util
from typing import Any, List, Tuple

from src.ai.core.response import TokenUsage
from src.ai.providers._remote import RemoteProvider
from src.ai.providers.base import LLMMessage


class OpenAIProvider(RemoteProvider):
    """Chat-completions provider for OpenAI models."""

    key = "openai"
    env_key = "OPENAI_API_KEY"

    def _sdk_available(self) -> bool:
        """Return ``True`` iff the ``openai`` SDK is importable."""
        return importlib.util.find_spec("openai") is not None

    def _client(self) -> Any:
        """Construct an OpenAI client (lazy import)."""
        from openai import OpenAI  # type: ignore

        return OpenAI(api_key=self._api_key(), timeout=self.settings.timeout)

    def _complete(
        self, client: Any, messages: List[LLMMessage], json_mode: bool
    ) -> Tuple[str, TokenUsage]:
        """Call chat.completions and return ``(text, usage)``."""
        kwargs: dict = {
            "model": self.model,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        completion = client.chat.completions.create(**kwargs)
        text = completion.choices[0].message.content or ""
        usage = TokenUsage()
        if getattr(completion, "usage", None):
            usage = TokenUsage(
                prompt_tokens=getattr(completion.usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(completion.usage, "completion_tokens", 0) or 0,
            )
        return text, usage
