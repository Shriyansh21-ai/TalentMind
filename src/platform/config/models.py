"""Enterprise configuration models (Module 6).

Per-tenant configuration: feature flags, licensing, usage limits, AI
provider/model configuration, branding, localization, regional settings and
custom prompt overrides. All configuration is data — it is read by the platform
but never fabricates or overrides the existing engines' own behaviour; the
custom-prompt overrides are an additive map the future integration layer may
consult.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity


class LicenseStatus(str, Enum):
    """State of a tenant's license."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class FeatureFlag(PlatformModel):
    """A single feature toggle with optional staged rollout."""

    key: str
    enabled: bool = False
    description: str = ""
    rollout_percentage: int = 100


class License(PlatformModel):
    """A tenant's license grant."""

    plan: str = "free"
    seats: int = 5
    status: LicenseStatus = LicenseStatus.ACTIVE
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    entitlements: list[str] = Field(default_factory=list)

    def is_valid_at(self, moment: datetime) -> bool:
        """Return whether the license is active and within its validity window."""
        if self.status != LicenseStatus.ACTIVE:
            return False
        if self.valid_from is not None and moment < self.valid_from:
            return False
        if self.valid_until is not None and moment >= self.valid_until:
            return False
        return True


class UsageLimit(PlatformModel):
    """A metered usage ceiling for a resource over a period."""

    resource: str
    limit: int | None = None
    period: str = "monthly"


class AIProviderConfig(PlatformModel):
    """AI provider configuration (references a key, never stores plaintext).

    Mirrors the shape of the existing ``AISettings`` so the platform can surface
    a tenant's chosen provider without importing or mutating the AI platform.
    """

    provider: str = "local"
    api_key_ref: str = ""
    base_url: str = ""
    enabled: bool = True


class ModelConfig(PlatformModel):
    """Model tuning parameters for a tenant's AI usage."""

    model: str = "deterministic-composer-v1"
    temperature: float = 0.2
    max_tokens: int = 1200


class LocalizationSettings(PlatformModel):
    """Language and formatting preferences."""

    language: str = "en"
    locale: str = "en-US"
    date_format: str = "YYYY-MM-DD"
    number_format: str = "1,234.56"
    currency: str = "USD"


class RegionalSettings(PlatformModel):
    """Region, timezone and data-residency preferences."""

    region: str = "global"
    timezone: str = "UTC"
    data_residency: str = "global"


class CustomPromptSettings(PlatformModel):
    """Additive per-tenant prompt overrides (key -> template text)."""

    overrides: dict[str, str] = Field(default_factory=dict)


class Configuration(TenantScopedEntity):
    """The full configuration bundle for a tenant."""

    feature_flags: dict[str, bool] = Field(default_factory=dict)
    license: License = Field(default_factory=License)
    usage_limits: list[UsageLimit] = Field(default_factory=list)
    ai_provider: AIProviderConfig = Field(default_factory=AIProviderConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    localization: LocalizationSettings = Field(default_factory=LocalizationSettings)
    regional: RegionalSettings = Field(default_factory=RegionalSettings)
    custom_prompts: CustomPromptSettings = Field(default_factory=CustomPromptSettings)
