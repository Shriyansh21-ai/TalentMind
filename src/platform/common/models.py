"""Base pydantic models shared across the platform.

Every persisted platform resource derives from :class:`Entity` (globally unique
id + timestamps). Every resource that belongs to a customer derives from
:class:`TenantScopedEntity`, which carries the ``tenant_id`` that the repository
layer uses to enforce isolation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.platform.common.clock import utcnow


class PlatformModel(BaseModel):
    """Common pydantic configuration for all platform models.

    * ``str_strip_whitespace`` — trims incidental whitespace on inputs.
    * ``validate_assignment`` — keeps invariants enforced after mutation.
    * ``populate_by_name`` — allows both field name and alias on input.
    * ``use_enum_values`` is intentionally **off** so enum members stay typed.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        populate_by_name=True,
        extra="ignore",
    )


class Entity(PlatformModel):
    """A uniquely-identified, timestamped platform resource.

    Attributes:
        id: Globally-unique, prefixed identifier.
        created_at: UTC creation time.
        updated_at: UTC time of the last mutation.
    """

    id: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def touch(self, moment: datetime | None = None) -> None:
        """Record a mutation by advancing ``updated_at``."""
        self.updated_at = moment or utcnow()


class TenantScopedEntity(Entity):
    """An :class:`Entity` that belongs to exactly one tenant.

    The ``tenant_id`` is the isolation key: the repository layer refuses to
    return or mutate an entity whose ``tenant_id`` does not match the active
    tenant context, making cross-tenant leakage structurally impossible.

    Attributes:
        tenant_id: Owning tenant id (isolation boundary).
        organization_id: Owning organization id (a tenant maps 1:1 to an org).
    """

    tenant_id: str
    organization_id: str


class Metadata(PlatformModel):
    """Free-form, namespaced key/value metadata attached to a resource.

    Values are constrained to JSON-serialisable scalars so metadata is always
    safe to persist, cache and emit over the API.
    """

    values: dict[str, Any] = Field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the metadata value for ``key`` (or ``default``)."""
        return self.values.get(key, default)

    def set(self, key: str, value: Any) -> "Metadata":
        """Return a copy with ``key`` set to ``value`` (immutable-style update)."""
        merged = {**self.values, key: value}
        return Metadata(values=merged)
