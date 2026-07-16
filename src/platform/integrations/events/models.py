"""Enterprise event model (Module 10).

The typed envelope every platform/integration event travels in. Events are
append-only and carry a monotonic ``sequence`` (assigned by the bus) so a topic
can be replayed in a deterministic order — the property a future Kafka/RabbitMQ
backend must also guarantee.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.clock import utcnow
from src.platform.common.models import Entity


class EventType(str, Enum):
    """The class of event, used for routing and governance."""

    DOMAIN = "domain"  # a business fact within the platform
    INTEGRATION = "integration"  # something happened with an external system
    SYSTEM = "system"  # platform lifecycle / operational


class EnterpriseEvent(Entity):
    """An immutable, ordered event published to a topic.

    Attributes:
        topic: Dotted routing key, e.g. ``"integration.workday.connected"``.
        event_type: Domain / integration / system classification.
        name: Human/action name (often the last topic segment).
        tenant_id: Owning tenant (``None`` for platform-wide events).
        sequence: Monotonic order assigned by the bus at publish time.
        payload: JSON-safe event body.
        occurred_at: When the event happened.
    """

    topic: str
    event_type: EventType = EventType.INTEGRATION
    name: str = ""
    tenant_id: str | None = None
    sequence: int = 0
    payload: dict[str, object] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utcnow)


class DeadLetterEntry(Entity):
    """A record of an event whose delivery to a subscriber failed."""

    event: EnterpriseEvent
    subscriber: str
    error: str = ""
    attempts: int = 1


class Subscription(Entity):
    """Registry bookkeeping for a topic subscription (state, not the handler)."""

    topic_pattern: str
    subscriber: str
    active: bool = True
