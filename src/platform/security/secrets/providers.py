"""Enterprise secret providers (Module 4).

The secret-backend seam and the offline local provider, plus *interface-only*
placeholders for HashiCorp Vault, Azure Key Vault, AWS Secrets Manager and GCP
Secret Manager. To avoid duplicating the obfuscation/encryption logic, this
module **reuses** the tenant-namespaced :class:`SecretProvider` /
:class:`InMemorySecretProvider` and the :class:`EncryptionProvider` seam already
defined for the Milestone 2 integration platform. No plaintext is ever stored
verbatim and no cloud call is made.
"""

from __future__ import annotations

from src.platform.integrations.common.secrets import (  # reuse — no duplication
    Base64ObfuscationProvider,
    EncryptionProvider,
    InMemorySecretProvider,
    SecretProvider,
)
from src.platform.security.common.errors import SecretError


class LocalSecretProvider(InMemorySecretProvider):
    """The offline, tenant-namespaced local secret provider (obfuscated store)."""

    def __init__(self, *, encryption: EncryptionProvider | None = None) -> None:
        super().__init__(name="local", encryption=encryption)


class _CloudSecretProvider:
    """Base for cloud secret-manager placeholders — describes, never connects."""

    name: str = "cloud"
    service: str = ""

    def describe(self) -> dict[str, str]:
        """Return non-secret descriptive metadata about this provider."""
        return {"name": self.name, "service": self.service, "status": "interface_only"}

    def _not_ready(self) -> SecretError:
        return SecretError(
            f"{self.name} is an architecture placeholder; bind a real client "
            "before use",
            code="secret_provider_not_configured",
        )

    def store(self, tenant_id: str, ref: str, value: str) -> None:
        raise self._not_ready()

    def read(self, tenant_id: str, ref: str) -> str | None:
        raise self._not_ready()

    def delete(self, tenant_id: str, ref: str) -> None:
        raise self._not_ready()

    def exists(self, tenant_id: str, ref: str) -> bool:
        raise self._not_ready()


class VaultSecretProvider(_CloudSecretProvider):
    name = "hashicorp_vault"
    service = "HashiCorp Vault"


class AzureKeyVaultProvider(_CloudSecretProvider):
    name = "azure_key_vault"
    service = "Azure Key Vault"


class AwsSecretsManagerProvider(_CloudSecretProvider):
    name = "aws_secrets_manager"
    service = "AWS Secrets Manager"


class GcpSecretManagerProvider(_CloudSecretProvider):
    name = "gcp_secret_manager"
    service = "GCP Secret Manager"


def cloud_provider_interfaces() -> list[_CloudSecretProvider]:
    """Return one instance of every cloud secret-manager placeholder."""
    return [
        VaultSecretProvider(),
        AzureKeyVaultProvider(),
        AwsSecretsManagerProvider(),
        GcpSecretManagerProvider(),
    ]


__all__ = [
    "SecretProvider",
    "EncryptionProvider",
    "Base64ObfuscationProvider",
    "LocalSecretProvider",
    "VaultSecretProvider",
    "AzureKeyVaultProvider",
    "AwsSecretsManagerProvider",
    "GcpSecretManagerProvider",
    "cloud_provider_interfaces",
]
