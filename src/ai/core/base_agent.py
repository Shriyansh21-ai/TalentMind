"""BaseAgent — the contract every AI agent implements.

The design goal (Module 1 / Future Vision): a new agent should require almost no
boilerplate. An agent declares its identity + output schema and implements two
small hooks — how to turn its typed input into (a) structured *evidence* and
(b) prompt placeholder values, plus the cache dimensions. Everything else
(prompt rendering, provider calls, retries, validation, safety, caching,
telemetry, deterministic fallback) is handled generically by :class:`AgentRunner`.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Type

from src.ai.core.metadata import AgentMetadata
from src.ai.prompts.loader import PromptLoader
from src.ai.providers.base import LLMMessage
from src.ai.schemas.base import BaseAIResponse


class BaseAgent(ABC):
    """Abstract base for all agents.

    Subclasses must define :attr:`metadata` and :attr:`output_schema`, and
    implement :meth:`build_evidence`, :meth:`prompt_values` and
    :meth:`cache_dimensions`.
    """

    #: Static identity of the agent.
    metadata: AgentMetadata
    #: Validated response schema produced by the agent.
    output_schema: Type[BaseAIResponse]

    # -- required hooks -----------------------------------------------------

    @abstractmethod
    def build_evidence(self, payload: Any) -> Dict[str, Any]:
        """Return the structured, authoritative evidence for ``payload``.

        This is the *only* factual input to the reasoning: it is embedded in the
        prompt for real providers and consumed by the deterministic composer for
        the offline provider. It must contain nothing the AI is allowed to invent.
        """

    @abstractmethod
    def prompt_values(self, payload: Any, evidence: Dict[str, Any]) -> Dict[str, str]:
        """Return agent-specific placeholder values for the user prompt.

        The runner automatically supplies the derived ``evidence_json`` and
        ``schema_fields`` placeholders, so subclasses typically only return things
        like ``{"jd": ...}``.
        """

    @abstractmethod
    def cache_dimensions(self, payload: Any) -> Tuple[str, str]:
        """Return ``(subject_id, scope)`` used for the cache key and telemetry.

        Typically ``(candidate_id, job_description)``.
        """

    # -- generic behaviour (rarely overridden) ------------------------------

    def schema_fields_description(self) -> str:
        """Return a readable list of the output schema's fields for the prompt."""
        return "\n".join(f"- {name}" for name in self.output_schema.field_names())

    def build_messages(
        self, payload: Any, loader: PromptLoader, evidence: Dict[str, Any]
    ) -> List[LLMMessage]:
        """Render the system + user messages from templates on disk.

        Loads ``{prompt_id}_system`` and ``{prompt_id}_user`` at the agent's
        prompt version, injecting the agent's placeholder values plus the derived
        ``evidence_json`` and ``schema_fields``.
        """
        prompt_id = self.metadata.prompt_id
        version = self.metadata.prompt_version

        system_text = loader.render(f"{prompt_id}_system", version)

        values: Dict[str, str] = {
            "evidence_json": json.dumps(evidence, ensure_ascii=False, indent=2),
            "schema_fields": self.schema_fields_description(),
        }
        values.update(self.prompt_values(payload, evidence))
        user_text = loader.render(f"{prompt_id}_user", version, **values)

        return [
            LLMMessage(role="system", content=system_text),
            LLMMessage(role="user", content=user_text),
        ]
