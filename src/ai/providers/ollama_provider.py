"""Ollama provider for locally-hosted open models (SDK imported lazily).

Requires the ``ollama`` package and a running Ollama server (``OLLAMA_HOST``,
default ``http://localhost:11434``). No API key is used. Only touched when the
provider is actually selected and used.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any

from src.ai.core.response import TokenUsage
from src.ai.providers._remote import RemoteProvider
from src.ai.providers.base import LLMMessage


class OllamaProvider(RemoteProvider):
    """Provider for a local Ollama server."""

    key = "ollama"
    env_key = ""  # no API key

    def _sdk_available(self) -> bool:
        """Return ``True`` iff the ``ollama`` SDK is importable."""
        return importlib.util.find_spec("ollama") is not None

    def health_check(self) -> bool:
        """Available if the SDK is importable (server reachability checked on use)."""
        try:
            return self._sdk_available()
        except Exception:
            return False

    def _client(self) -> Any:
        """Construct an Ollama client bound to the configured host (lazy import)."""
        import ollama  # type: ignore

        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        return ollama.Client(host=host)

    def _complete(
        self, client: Any, messages: list[LLMMessage], json_mode: bool
    ) -> tuple[str, TokenUsage]:
        """Call chat and return ``(text, usage)``."""
        response = client.chat(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            format="json" if json_mode else "",
            options={
                "temperature": self.settings.temperature,
                "num_predict": self.settings.max_tokens,
            },
        )
        text = (response.get("message", {}) or {}).get("content", "") or ""
        usage = TokenUsage(
            prompt_tokens=response.get("prompt_eval_count", 0) or 0,
            completion_tokens=response.get("eval_count", 0) or 0,
        )
        return text, usage
