"""Module 4 — Enterprise Secrets Framework.

A :class:`SecretManager` over a swappable :class:`SecretProvider` (obfuscated
local store, plus Vault / Azure Key Vault / AWS Secrets Manager / GCP Secret
Manager interface placeholders), with versioning, expiration, rotation policies
and access tracking. Never exposes plaintext except at the point of use.
"""

from __future__ import annotations

from src.platform.security.secrets.manager import (
    AccessRecord,
    SecretManager,
    SecretMetadata,
    SecretStatus,
)
from src.platform.security.secrets.providers import (
    AwsSecretsManagerProvider,
    AzureKeyVaultProvider,
    GcpSecretManagerProvider,
    LocalSecretProvider,
    SecretProvider,
    VaultSecretProvider,
    cloud_provider_interfaces,
)

__all__ = [
    "SecretProvider",
    "LocalSecretProvider",
    "VaultSecretProvider",
    "AzureKeyVaultProvider",
    "AwsSecretsManagerProvider",
    "GcpSecretManagerProvider",
    "cloud_provider_interfaces",
    "SecretManager",
    "SecretMetadata",
    "SecretStatus",
    "AccessRecord",
]
