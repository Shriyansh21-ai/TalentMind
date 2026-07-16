"""Enterprise audit models (Module 3).

A central, immutable, hash-chained audit entry spanning every platform domain
(authentication, authorization, runtime, integration, AI, platform, security,
configuration). Entries carry a correlation id so a single logical operation can
be traced across subsystems, and a per-tenant hash chain makes tampering
detectable. This is a *new central* service — separate from, and additive to,
the Milestone 1 platform audit.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import Metadata, TenantScopedEntity
from src.platform.security.common.models import Severity


class AuditEventType(str, Enum):
    """The domain a central audit entry belongs to."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RUNTIME = "runtime"
    INTEGRATION = "integration"
    AI = "ai"
    PLATFORM = "platform"
    SECURITY = "security"
    CONFIGURATION = "configuration"


class AuditOutcome(str, Enum):
    """Whether the audited action succeeded."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditEntry(TenantScopedEntity):
    """A single immutable, hash-chained central audit entry."""

    sequence: int = 0
    event_type: AuditEventType = AuditEventType.PLATFORM
    action: str = ""
    actor_id: str = "system"
    resource_type: str = ""
    resource_id: str = ""
    correlation_id: str = ""
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    severity: Severity = Severity.INFO
    source: str = ""  # originating subsystem
    metadata: Metadata = Field(default_factory=Metadata)
    prev_hash: str = ""
    hash: str = ""


class RetentionPolicy(TenantScopedEntity):
    """A per-tenant retention policy (days) by event type."""

    default_days: int = 365
    by_event_type: dict[str, int] = Field(default_factory=dict)

    def days_for(self, event_type: AuditEventType) -> int:
        """Return the retention window (days) for ``event_type``."""
        return self.by_event_type.get(event_type.value, self.default_days)
