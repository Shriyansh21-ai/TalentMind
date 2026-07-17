"""Template-method base for network-backed (remote) LLM providers.

Captures everything the vendor providers share — key lookup, timing, the JSON
directive, error wrapping — so each concrete provider only implements the small
vendor-specific bits (``_sdk_available``, ``_client``, ``_complete``). This keeps
the providers DRY and makes adding a new vendor a ~30-line exercise.
"""

from __future__ import annotations

import json
import os
import time
from abc import abstractmethod
from typing import Any

from src.ai.core.exceptions import ProviderError, ProviderUnavailableError
from src.ai.core.response import AgentResponse, TokenUsage
from src.ai.providers.base import BaseLLMProvider, LLMMessage
from src.ai.utils.json_utils import extract_json_object


class RemoteProvider(BaseLLMProvider):
    """Base for providers that call an external API over the network.

    Subclasses set :attr:`env_key` and implement :meth:`_sdk_available`,
    :meth:`_client` and :meth:`_complete`.
    """

    env_key: str = ""

    # -- helpers ------------------------------------------------------------

    def _api_key(self) -> str | None:
        """Return the configured API key from the environment (or ``None``)."""
        return os.environ.get(self.env_key) if self.env_key else None

    @staticmethod
    def _json_directive(schema: dict[str, Any]) -> str:
        """Return a system instruction forcing schema-valid JSON output."""
        return (
            "You must respond with a single JSON object and nothing else. "
            "Do not wrap it in markdown. It must validate against this JSON "
            f"schema:\n{json.dumps(schema)}"
        )

    # -- vendor-specific seams ---------------------------------------------

    @abstractmethod
    def _sdk_available(self) -> bool:
        """Return ``True`` iff the vendor SDK can be imported."""

    @abstractmethod
    def _client(self) -> Any:
        """Construct and return the vendor client (lazily imports the SDK)."""

    @abstractmethod
    def _complete(
        self, client: Any, messages: list[LLMMessage], json_mode: bool
    ) -> tuple[str, TokenUsage]:
        """Perform one completion; return ``(text, usage)``."""

    # -- BaseLLMProvider ----------------------------------------------------

    def health_check(self) -> bool:
        """Cheap readiness check: SDK importable and API key present.

        Intentionally performs no network round-trip so it is safe (and fast) to
        call during UI rendering and tests.
        """
        try:
            return bool(self._api_key()) and self._sdk_available()
        except Exception:
            return False

    def generate(self, messages: list[LLMMessage], **kwargs: Any) -> AgentResponse:
        """Generate free-form text via the vendor API."""
        return self._run(messages, json_mode=False)

    def generate_json(
        self,
        messages: list[LLMMessage],
        *,
        schema: dict[str, Any],
        schema_name: str,
        evidence: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Generate a JSON object; the schema directive is prepended as a system msg."""
        directive = LLMMessage(role="system", content=self._json_directive(schema))
        response = self._run([directive, *messages], json_mode=True)
        response.text = extract_json_object(response.text)
        return response

    # -- internal -----------------------------------------------------------

    def _run(self, messages: list[LLMMessage], json_mode: bool) -> AgentResponse:
        """Shared timing + error-wrapping around a vendor completion."""
        if not self.health_check():
            raise ProviderUnavailableError(
                f"Provider {self.key!r} is not available (missing SDK or {self.env_key})."
            )
        start = time.perf_counter()
        try:
            client = self._client()
            text, usage = self._complete(client, messages, json_mode)
        except ProviderError:
            raise
        except Exception as exc:  # normalize any vendor error
            raise ProviderError(f"{self.key} call failed: {exc}") from exc
        latency_ms = (time.perf_counter() - start) * 1000.0
        return AgentResponse(
            text=text,
            provider=self.key,
            model=self.model,
            latency_ms=latency_ms,
            usage=usage,
        )
