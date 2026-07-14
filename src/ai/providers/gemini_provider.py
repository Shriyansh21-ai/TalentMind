"""Google Gemini provider (SDK imported lazily).

Requires the ``google-generativeai`` package and ``GOOGLE_API_KEY``. Only touched
when the provider is actually selected and used.
"""

from __future__ import annotations

import importlib.util
from typing import Any, List, Tuple

from src.ai.core.response import TokenUsage
from src.ai.providers._remote import RemoteProvider
from src.ai.providers.base import LLMMessage


class GeminiProvider(RemoteProvider):
    """Provider for Google Gemini models."""

    key = "gemini"
    env_key = "GOOGLE_API_KEY"

    def _sdk_available(self) -> bool:
        """Return ``True`` iff the ``google.generativeai`` SDK is importable."""
        return importlib.util.find_spec("google.generativeai") is not None

    def _client(self) -> Any:
        """Configure and return a Gemini model handle (lazy import)."""
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=self._api_key())
        return genai.GenerativeModel(self.model)

    def _complete(
        self, client: Any, messages: List[LLMMessage], json_mode: bool
    ) -> Tuple[str, TokenUsage]:
        """Call generate_content and return ``(text, usage)``.

        Gemini has no distinct system role, so system messages are folded into the
        prompt as a leading instruction block.
        """
        system_parts = [m.content for m in messages if m.role == "system"]
        body_parts = [
            m.content for m in messages if m.role in ("user", "assistant")
        ]
        prompt = "\n\n".join([*system_parts, *body_parts])

        generation_config: dict = {
            "temperature": self.settings.temperature,
            "max_output_tokens": self.settings.max_tokens,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        response = client.generate_content(prompt, generation_config=generation_config)
        text = getattr(response, "text", "") or ""

        usage = TokenUsage()
        meta = getattr(response, "usage_metadata", None)
        if meta is not None:
            usage = TokenUsage(
                prompt_tokens=getattr(meta, "prompt_token_count", 0) or 0,
                completion_tokens=getattr(meta, "candidates_token_count", 0) or 0,
            )
        return text, usage
