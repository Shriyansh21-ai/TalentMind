"""Platform audit models (Module 9).

Platform-level audit events — authentication, authorization, settings and
structural changes — kept deliberately **separate** from the Phase 5 hiring
audit (which explains hiring decisions). Events form a per-tenant, hash-chained
sequence so tampering is detectable, laying the groundwork for future
compliance attestations.
"""

from __future__ import annotations

from enum import Enum

from src.platform.common.models import Metadata, TenantScopedEntity
from pydantic import Field


class AuditCategory(str, Enum):
    """The domain an audit event belongs to."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SETTINGS = "settings"
    WORKSPACE = "workspace"
    PERMISSION = "permission"
    ORGANIZATION = "organization"
    CONFIGURATION = "configuration"
    SUBSCRIPTION = "subscription"
    SECURITY = "security"


class AuditOutcome(str, Enum):
    """Whether the audited action succeeded."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditEvent(TenantScopedEntity):
    """A single, immutable audit record within a tenant's chain.

    Attributes:
        sequence: Monotonic per-tenant sequence number.
        category / action: What happened.
        actor_id: The principal responsible (``system`` if platform-initiated).
        target_type / target_id: The resource acted upon.
        outcome: Result of the action.
        ip_address: Source IP where known.
        metadata: Additional structured context.
        prev_hash / hash: Tamper-evident chain links.
    """

    sequence: int = 0
    category: AuditCategory = AuditCategory.SECURITY
    action: str = ""
    actor_id: str = "system"
    target_type: str = ""
    target_id: str = ""
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    ip_address: str = ""
    metadata: Metadata = Field(default_factory=Metadata)
    prev_hash: str = ""
    hash: str = ""
