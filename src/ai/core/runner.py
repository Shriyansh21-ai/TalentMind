"""AgentRunner — the generic execution engine for every agent.

Responsibilities (so agents don't have to): context creation, cache lookup,
provider selection, prompt rendering, the retry loop, JSON + schema validation,
safety review, deterministic fallback, cache write-back, and telemetry. This is
where the platform's cross-cutting concerns live, once.

All collaborators are injected (settings, loader, cache, telemetry, safety,
context builder, provider factory), so the runner is fully testable and every
policy is swappable — SOLID by construction.
"""

from __future__ import annotations

import time
from typing import Any, Callable, List, Optional, Tuple

from src.ai.config.settings import AISettings
from src.ai.cache.base import BaseCache, NullCache
from src.ai.cache.file_cache import FileCache
from src.ai.cache.key import build_cache_key
from src.ai.core.agent_config import AgentConfig
from src.ai.core.base_agent import BaseAgent
from src.ai.core.exceptions import (
    JSONParseError,
    ProviderError,
    SchemaValidationError,
)
from src.ai.core.response import AgentResult, AgentStatus, TokenUsage
from src.ai.memory.context_builder import ContextBuilder
from src.ai.providers.base import BaseLLMProvider, LLMMessage
from src.ai.providers.factory import get_provider as default_get_provider
from src.ai.providers.local import LocalHeuristicProvider
from src.ai.telemetry.logger import TelemetryLogger, get_default_logger
from src.ai.telemetry.models import TelemetryEvent
from src.ai.validators.json_validator import validate_text
from src.ai.validators.safety import SafetyGuard

_CORRECTIVE = LLMMessage(
    role="user",
    content=(
        "Your previous response was not valid JSON matching the required schema. "
        "Return ONLY a single JSON object with exactly the required fields."
    ),
)


class AgentRunner:
    """Runs an agent end-to-end and returns a standardized :class:`AgentResult`."""

    def __init__(
        self,
        settings: Optional[AISettings] = None,
        *,
        cache: Optional[BaseCache] = None,
        telemetry: Optional[TelemetryLogger] = None,
        safety: Optional[SafetyGuard] = None,
        context_builder: Optional[ContextBuilder] = None,
        provider_selector: Optional[
            Callable[[AISettings], Tuple[BaseLLMProvider, list]]
        ] = None,
    ) -> None:
        """Wire the runner's collaborators (all optional; sane defaults used)."""
        self.settings = settings or AISettings.from_env()
        self.cache = cache or (
            FileCache(self.settings.cache_dir)
            if self.settings.cache_enabled
            else NullCache()
        )
        self.telemetry = telemetry or get_default_logger(self.settings.telemetry_dir)
        self.safety = safety or SafetyGuard()
        self.context_builder = context_builder or ContextBuilder()
        self._get_provider = provider_selector or default_get_provider

    # -- public API ---------------------------------------------------------

    def run(
        self,
        agent: BaseAgent,
        payload: Any,
        config: Optional[AgentConfig] = None,
    ) -> AgentResult:
        """Execute ``agent`` on ``payload`` and return a standardized result."""
        config = config or AgentConfig()
        schema_cls = agent.output_schema

        # Structural safety: agents can never emit scores.
        self.safety.assert_schema_is_score_free(schema_cls)

        evidence = agent.build_evidence(payload)
        subject_id, scope = agent.cache_dimensions(payload)
        context = self.context_builder.build(
            agent_name=agent.metadata.name,
            payload=payload,
            settings=self.settings,
            subject_id=subject_id,
            scope=scope,
        )

        cache_key = self._build_key(agent, subject_id, scope)

        # 1) Cache lookup.
        if config.use_cache and not config.force_refresh:
            cached = self._read_cache(cache_key, schema_cls)
            if cached is not None:
                result = AgentResult(
                    status=AgentStatus.CACHED,
                    agent=agent.metadata.name,
                    agent_version=agent.metadata.version,
                    provider=self.settings.provider,
                    model=self.settings.model,
                    data=cached,
                    cache_hit=True,
                )
                self._emit_telemetry(context, result)
                return result

        # 2) Live run.
        result = self._execute(agent, payload, evidence, schema_cls, config)

        # 3) Cache write-back on any usable result.
        if result.ok and config.use_cache:
            self.cache.set(
                cache_key,
                {
                    "schema": schema_cls.schema_name(),
                    "agent_version": agent.metadata.version,
                    "provider": result.provider,
                    "model": result.model,
                    "data": result.data.to_dict(),
                },
            )

        self._emit_telemetry(context, result)
        return result

    def peek(self, agent: BaseAgent, payload: Any) -> Optional[AgentResult]:
        """Return a cached result without ever calling a provider.

        Used by the UI to auto-load a previously-generated analysis on demand
        (Module 11: no provider work happens unless the recruiter explicitly asks
        for a fresh analysis).
        """
        if not self.settings.cache_enabled:
            return None
        subject_id, scope = agent.cache_dimensions(payload)
        cache_key = self._build_key(agent, subject_id, scope)
        cached = self._read_cache(cache_key, agent.output_schema)
        if cached is None:
            return None
        return AgentResult(
            status=AgentStatus.CACHED,
            agent=agent.metadata.name,
            agent_version=agent.metadata.version,
            provider=self.settings.provider,
            model=self.settings.model,
            data=cached,
            cache_hit=True,
        )

    # -- internals ----------------------------------------------------------

    def _build_key(self, agent: BaseAgent, subject_id: str, scope: str) -> str:
        """Build the composite cache key for ``agent`` on ``(subject_id, scope)``."""
        return build_cache_key(
            agent=agent.metadata.name,
            agent_version=agent.metadata.version,
            prompt_version=agent.metadata.prompt_version,
            provider=self.settings.provider,
            model=self.settings.model,
            subject_id=subject_id,
            scope=scope,
        )

    def _read_cache(self, cache_key: str, schema_cls) -> Optional[Any]:
        """Return a validated cached payload, or ``None`` on miss/mismatch."""
        cached = self.cache.get(cache_key)
        if not cached or "data" not in cached:
            return None
        try:
            return schema_cls(**cached["data"])
        except Exception:
            return None  # treat stale/incompatible cache as a miss

    def _execute(
        self, agent, payload, evidence, schema_cls, config: AgentConfig
    ) -> AgentResult:
        """Provider selection, retries, validation, safety and fallback."""
        max_retries = (
            config.max_retries if config.max_retries is not None else self.settings.max_retries
        )
        warnings: List[str] = []

        provider, provider_warnings = self._get_provider(self.settings)
        warnings.extend(provider_warnings)

        messages = agent.build_messages(payload, agent_loader(agent), evidence)
        schema = schema_cls.json_schema()
        schema_name = schema_cls.schema_name()

        start = time.perf_counter()
        instance, usage, retries, last_error = self._attempt(
            provider, messages, schema, schema_name, evidence, schema_cls, max_retries
        )

        provider_used: BaseLLMProvider = provider

        # Deterministic fallback if a real provider produced nothing usable.
        if instance is None and config.allow_fallback and not provider.is_deterministic:
            if not self.settings.strict:
                warnings.append(
                    f"Provider {provider.key!r} failed ({last_error}); used "
                    "deterministic composer instead."
                )
                fallback = LocalHeuristicProvider(self.settings)
                instance, usage, _, last_error = self._attempt(
                    fallback, messages, schema, schema_name, evidence, schema_cls, 0
                )
                provider_used = fallback

        latency_ms = (time.perf_counter() - start) * 1000.0

        if instance is None:
            return AgentResult(
                status=AgentStatus.FAILED,
                agent=agent.metadata.name,
                agent_version=agent.metadata.version,
                provider=provider_used.key,
                model=self.settings.model,
                data=None,
                retries=retries,
                latency_ms=latency_ms,
                usage=usage,
                warnings=warnings,
                error=str(last_error) if last_error else "Unknown AI failure",
            )

        # Safety review (soft).
        instance, report = self.safety.review(instance, evidence)
        warnings.extend(report.warnings)

        substituted = provider_used.key != self.settings.provider
        status = AgentStatus.FALLBACK if substituted else AgentStatus.SUCCESS

        return AgentResult(
            status=status,
            agent=agent.metadata.name,
            agent_version=agent.metadata.version,
            provider=provider_used.key,
            model=self.settings.model,
            data=instance,
            retries=retries,
            latency_ms=latency_ms,
            usage=usage,
            warnings=warnings,
        )

    def _attempt(
        self,
        provider: BaseLLMProvider,
        messages,
        schema,
        schema_name,
        evidence,
        schema_cls,
        max_retries: int,
    ):
        """Call a provider up to ``max_retries+1`` times; validate each response.

        Returns ``(instance_or_None, usage, retries_used, last_error)``.
        """
        usage = TokenUsage()
        last_error: Optional[Exception] = None
        retries = 0

        # Deterministic providers are exact — a single attempt, no corrections.
        attempts = 1 if provider.is_deterministic else max_retries + 1

        for attempt in range(attempts):
            call_messages = messages if attempt == 0 else [*messages, _CORRECTIVE]
            try:
                response = provider.generate_json(
                    call_messages,
                    schema=schema,
                    schema_name=schema_name,
                    evidence=evidence,
                )
                usage = response.usage
                instance = validate_text(response.text, schema_cls)
                return instance, usage, retries, None
            except (JSONParseError, SchemaValidationError) as exc:
                last_error = exc
                retries = attempt + 1 if attempt + 1 < attempts else attempt
                continue
            except ProviderError as exc:
                last_error = exc
                break  # provider itself is broken; stop retrying

        return None, usage, retries, last_error

    def _emit_telemetry(self, context, result: AgentResult) -> None:
        """Record a telemetry event for a completed run."""
        self.telemetry.record(
            TelemetryEvent(
                request_id=context.request_id,
                agent=result.agent,
                agent_version=result.agent_version,
                provider=result.provider,
                model=result.model,
                status=result.status.value,
                latency_ms=round(result.latency_ms, 2),
                prompt_tokens=result.usage.prompt_tokens,
                completion_tokens=result.usage.completion_tokens,
                cache_hit=result.cache_hit,
                retries=result.retries,
                subject_id=context.subject_id,
                warnings=list(result.warnings),
                error=result.error,
            )
        )


# The prompt loader is agent-agnostic; a single default instance is reused.
from src.ai.prompts.loader import get_default_loader  # noqa: E402


def agent_loader(_agent: BaseAgent):
    """Return the shared prompt loader (indirection kept for future per-agent dirs)."""
    return get_default_loader()
