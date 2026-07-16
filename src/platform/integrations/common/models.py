"""Core integration domain models (Module 1).

The vocabulary the whole Enterprise Integration Platform is built from:

* :class:`IntegrationDefinition` — a *platform-level* catalogue blueprint for a
  provider (Workday, Greenhouse, Slack …). Not tenant-scoped; it describes what
  a provider *is* and *can do*.
* :class:`IntegrationConfiguration` — the tenant-supplied settings for an
  installed integration (never carries plaintext secrets — only a credential
  reference).
* :class:`Integration` — a *tenant-scoped* installed instance binding a
  definition to a tenant's configuration, connection status and health.
* :class:`IntegrationMetadata`, :class:`IntegrationCapabilities`,
  :class:`IntegrationHealth`, :class:`IntegrationStatus` — the descriptive and
  runtime facets referenced by the above.

All models are pydantic and JSON-safe; the runtime records are tenant-scoped so
the repository layer isolates one tenant's integrations from another's.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.clock import utcnow
from src.platform.common.models import Metadata, PlatformModel, TenantScopedEntity


class ProviderCategory(str, Enum):
    """The ecosystem family a provider belongs to."""

    HRIS = "hris"
    ATS = "ats"
    CALENDAR = "calendar"
    COMMUNICATION = "communication"
    DOCUMENT = "document"
    CUSTOM = "custom"


class AuthScheme(str, Enum):
    """How a provider authenticates (architecture only — no flows implemented)."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER_TOKEN = "bearer_token"
    SAML = "saml"
    SERVICE_ACCOUNT = "service_account"
    NONE = "none"


class IntegrationStatus(str, Enum):
    """The connection lifecycle state of an installed integration."""

    NOT_CONNECTED = "not_connected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    ERROR = "error"
    EXPIRED = "expired"
    DISABLED = "disabled"


class HealthState(str, Enum):
    """A coarse health signal, independent of connection lifecycle."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SyncDirection(str, Enum):
    """Which way data flows for a capability."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class IntegrationCapabilities(PlatformModel):
    """A declarative description of what a provider can do.

    Providers advertise capabilities so the platform can reason about them
    (enable sync only if ``supports_incremental_sync``, expose a webhook UI only
    if ``supports_webhooks``) without special-casing any single provider.
    """

    supports_read: bool = True
    supports_write: bool = False
    supports_full_sync: bool = False
    supports_incremental_sync: bool = False
    supports_webhooks: bool = False
    supports_realtime: bool = False
    supports_bulk: bool = False
    direction: SyncDirection = SyncDirection.INBOUND
    entities: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)

    def has_entity(self, entity: str) -> bool:
        """Return whether the provider exposes ``entity`` (e.g. ``"employee"``)."""
        return entity in self.entities


class IntegrationMetadata(PlatformModel):
    """Human- and machine-facing descriptive metadata for a provider."""

    display_name: str
    vendor: str = ""
    category: ProviderCategory = ProviderCategory.CUSTOM
    description: str = ""
    website: str = ""
    docs_url: str = ""
    logo_emoji: str = "🔌"
    auth_schemes: list[AuthScheme] = Field(default_factory=lambda: [AuthScheme.OAUTH2])
    tags: list[str] = Field(default_factory=list)
    version: str = "1.0.0"


class IntegrationDefinition(PlatformModel):
    """A platform-level catalogue blueprint describing an available provider.

    A definition is *not* tenant-scoped: it is the same for every tenant and is
    produced by a provider's :meth:`describe`. Installing it for a tenant
    produces a tenant-scoped :class:`Integration`.
    """

    key: str
    metadata: IntegrationMetadata
    capabilities: IntegrationCapabilities = Field(default_factory=IntegrationCapabilities)
    beta: bool = False

    @property
    def category(self) -> ProviderCategory:
        """Return the provider category (from metadata)."""
        return self.metadata.category


class IntegrationConfiguration(PlatformModel):
    """Tenant-supplied configuration for an installed integration.

    Deliberately carries **no plaintext secret** — only a ``credential_ref`` that
    points at a secret held by a
    :class:`~src.platform.integrations.common.secrets.SecretProvider`.
    """

    settings: dict[str, object] = Field(default_factory=dict)
    credential_ref: str = ""
    enabled_scopes: list[str] = Field(default_factory=list)
    sync_enabled: bool = False
    webhook_enabled: bool = False

    def get(self, key: str, default: object = None) -> object:
        """Return a configuration setting (or ``default``)."""
        return self.settings.get(key, default)


class IntegrationHealth(PlatformModel):
    """A point-in-time health snapshot for an installed integration."""

    state: HealthState = HealthState.UNKNOWN
    message: str = ""
    latency_ms: float = 0.0
    consecutive_failures: int = 0
    checked_at: datetime = Field(default_factory=utcnow)

    @property
    def is_healthy(self) -> bool:
        """Return whether the integration is currently healthy."""
        return self.state == HealthState.HEALTHY


class Integration(TenantScopedEntity):
    """A tenant-scoped installed integration instance.

    Binds a catalogue :class:`IntegrationDefinition` (by ``definition_key``) to a
    tenant's :class:`IntegrationConfiguration`, tracking connection status and
    the latest :class:`IntegrationHealth`. The repository layer isolates these
    per tenant, so one tenant can never see another's installed integrations.
    """

    definition_key: str
    display_name: str = ""
    category: ProviderCategory = ProviderCategory.CUSTOM
    status: IntegrationStatus = IntegrationStatus.NOT_CONNECTED
    configuration: IntegrationConfiguration = Field(default_factory=IntegrationConfiguration)
    health: IntegrationHealth = Field(default_factory=IntegrationHealth)
    metadata: Metadata = Field(default_factory=Metadata)
    last_connected_at: datetime | None = None
    last_synced_at: datetime | None = None

    @property
    def is_connected(self) -> bool:
        """Return whether the integration is in a usable, connected state."""
        return self.status in (IntegrationStatus.CONNECTED, IntegrationStatus.DEGRADED)
