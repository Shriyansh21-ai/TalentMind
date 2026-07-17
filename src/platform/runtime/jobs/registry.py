"""Job registry (Module 1).

A catalogue of :class:`JobDefinition` blueprints and their (optional) handler
callables. Handlers are plain callables registered by key — the registry never
holds business logic itself, and a job can be *defined* without a handler bound
(architecture-only), in which case executing it is an explicit no-op.
"""

from __future__ import annotations

from collections.abc import Callable

from src.platform.common.errors import ConflictError
from src.platform.runtime.common.errors import JobNotFoundError
from src.platform.runtime.jobs.models import JobDefinition

#: A job handler receives the job payload and returns a JSON-safe result dict.
JobHandler = Callable[[dict], dict]


class JobRegistry:
    """Registers job definitions and their optional handlers."""

    def __init__(self) -> None:
        self._definitions: dict[str, JobDefinition] = {}
        self._handlers: dict[str, JobHandler] = {}

    def register(
        self, definition: JobDefinition, handler: JobHandler | None = None
    ) -> JobDefinition:
        """Register a definition (and optionally its handler) by key."""
        if definition.key in self._definitions:
            raise ConflictError(f"job definition '{definition.key}' already registered")
        self._definitions[definition.key] = definition
        if handler is not None:
            self._handlers[definition.key] = handler
        return definition

    def has(self, key: str) -> bool:
        """Return whether a definition is registered under ``key``."""
        return key in self._definitions

    def get(self, key: str) -> JobDefinition:
        """Return a definition or raise :class:`JobNotFoundError`."""
        definition = self._definitions.get(key)
        if definition is None:
            raise JobNotFoundError(f"job definition '{key}' not registered")
        return definition

    def handler(self, key: str) -> JobHandler | None:
        """Return the handler bound to ``key`` (or ``None`` if unbound)."""
        return self._handlers.get(key)

    def definitions(self) -> list[JobDefinition]:
        """Return every registered definition."""
        return list(self._definitions.values())
