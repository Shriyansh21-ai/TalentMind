"""Exception hierarchy for the AI Platform.

A single, well-typed hierarchy so callers can catch broadly (``AgentException``)
or narrowly (e.g. ``SchemaValidationError``). No business-logic exceptions live
here — only AI-platform concerns.
"""

from __future__ import annotations


class AgentException(Exception):
    """Base class for every AI-platform error."""


class AgentConfigError(AgentException):
    """Raised when an agent or the platform is misconfigured."""


class AgentNotFoundError(AgentException):
    """Raised when a requested agent is not present in the registry."""


class ProviderError(AgentException):
    """Base class for provider-layer failures."""


class ProviderUnavailableError(ProviderError):
    """Raised when a provider cannot be used (missing SDK, key, or host down)."""


class ProviderTimeoutError(ProviderError):
    """Raised when a provider call exceeds the configured timeout."""


class PromptError(AgentException):
    """Base class for prompt-management failures."""


class PromptNotFoundError(PromptError):
    """Raised when a prompt template / version cannot be located."""


class PromptRenderError(PromptError):
    """Raised when a template cannot be rendered (e.g. missing placeholder)."""


class OutputValidationError(AgentException):
    """Base class for structured-output failures."""


class JSONParseError(OutputValidationError):
    """Raised when a provider response cannot be parsed as JSON."""


class SchemaValidationError(OutputValidationError):
    """Raised when parsed JSON does not satisfy the response schema."""


class SafetyViolationError(AgentException):
    """Raised when a response violates a platform safety rule."""
