"""Shared foundation for the Enterprise Integration Platform (Module 1).

Base models, the provider seam, the registry/discovery, credential/secret
abstractions and the integration error hierarchy — reused by every provider
family (HRIS, ATS, calendar, communication, documents) and by the manager,
gateway, webhook, sync and event modules.
"""

from __future__ import annotations

from src.platform.integrations.common.errors import (
    CapabilityNotSupportedError,
    ConnectionFailedError,
    CredentialError,
    IntegrationError,
    IntegrationNotConnectedError,
    ProviderConfigurationError,
    ProviderNotFoundError,
    RateLimitExceededError,
    SyncConflictError,
    WebhookVerificationError,
)
from src.platform.integrations.common.models import (
    AuthScheme,
    HealthState,
    Integration,
    IntegrationCapabilities,
    IntegrationConfiguration,
    IntegrationDefinition,
    IntegrationHealth,
    IntegrationMetadata,
    IntegrationStatus,
    ProviderCategory,
    SyncDirection,
)
from src.platform.integrations.common.provider import (
    BaseIntegrationProvider,
    IntegrationProvider,
)
from src.platform.integrations.common.registry import (
    IntegrationRegistry,
    build_default_registry,
)
from src.platform.integrations.common.secrets import (
    Base64ObfuscationProvider,
    CredentialType,
    CredentialVault,
    EncryptionProvider,
    InMemorySecretProvider,
    SecretProvider,
    SecretRef,
    VaultSecretProvider,
)

__all__ = [
    # errors
    "IntegrationError",
    "ProviderNotFoundError",
    "ProviderConfigurationError",
    "IntegrationNotConnectedError",
    "ConnectionFailedError",
    "CredentialError",
    "CapabilityNotSupportedError",
    "SyncConflictError",
    "WebhookVerificationError",
    "RateLimitExceededError",
    # models
    "ProviderCategory",
    "AuthScheme",
    "IntegrationStatus",
    "HealthState",
    "SyncDirection",
    "IntegrationCapabilities",
    "IntegrationMetadata",
    "IntegrationDefinition",
    "IntegrationConfiguration",
    "IntegrationHealth",
    "Integration",
    # provider
    "IntegrationProvider",
    "BaseIntegrationProvider",
    # registry
    "IntegrationRegistry",
    "build_default_registry",
    # secrets
    "SecretRef",
    "CredentialType",
    "SecretProvider",
    "InMemorySecretProvider",
    "VaultSecretProvider",
    "EncryptionProvider",
    "Base64ObfuscationProvider",
    "CredentialVault",
]
