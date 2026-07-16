"""Integration-platform exception hierarchy (Phase 6 / Milestone 2).

Extends the platform-wide :class:`~src.platform.common.errors.PlatformError`
hierarchy with errors specific to the Enterprise Integration Platform, so
callers can catch broadly (:class:`IntegrationError`) or narrowly
(e.g. :class:`ProviderNotFoundError`). No business-logic exceptions live here —
only enterprise integration concerns (providers, connections, credentials,
webhooks, synchronization, events).
"""

from __future__ import annotations

from src.platform.common.errors import PlatformError


class IntegrationError(PlatformError):
    """Base class for every enterprise-integration error."""

    code = "integration_error"


class ProviderNotFoundError(IntegrationError):
    """Raised when no provider is registered under a requested key."""

    code = "provider_not_found"


class ProviderConfigurationError(IntegrationError):
    """Raised when an integration configuration fails a provider invariant."""

    code = "provider_configuration_error"


class IntegrationNotConnectedError(IntegrationError):
    """Raised when an operation requires an active, connected integration."""

    code = "integration_not_connected"


class ConnectionFailedError(IntegrationError):
    """Raised when a (simulated) connection attempt cannot be established."""

    code = "connection_failed"


class CredentialError(IntegrationError):
    """Raised when a credential is missing, malformed or expired."""

    code = "credential_error"


class CapabilityNotSupportedError(IntegrationError):
    """Raised when a provider is asked for a capability it does not declare."""

    code = "capability_not_supported"


class SyncConflictError(IntegrationError):
    """Raised when a synchronization detects an unresolved data conflict."""

    code = "sync_conflict"


class WebhookVerificationError(IntegrationError):
    """Raised when an inbound webhook signature or replay check fails."""

    code = "webhook_verification_failed"


class RateLimitExceededError(IntegrationError):
    """Raised when an integration exceeds its configured rate budget."""

    code = "integration_rate_limit_exceeded"
