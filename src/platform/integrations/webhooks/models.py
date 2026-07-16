"""Webhook platform models (Module 8).

Tenant-scoped records for outgoing and incoming webhooks: subscriptions (where
to deliver, which events, the signing secret reference), individual delivery
attempts with their status and retry bookkeeping, and inbound receipts used for
replay protection.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import TenantScopedEntity


class WebhookDirection(str, Enum):
    """Whether a subscription sends (outgoing) or receives (incoming) events."""

    OUTGOING = "outgoing"
    INCOMING = "incoming"


class DeliveryStatus(str, Enum):
    """Lifecycle of a single webhook delivery attempt."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class WebhookSubscription(TenantScopedEntity):
    """A tenant's registration to send/receive events over a webhook.

    Attributes:
        url: Destination (outgoing) or expected source (incoming) URL.
        direction: Outgoing or incoming.
        event_filters: Topic patterns this subscription cares about (``*`` ok).
        secret_ref: Reference to the HMAC signing secret (never the secret).
        active: Whether the subscription is enabled.
        max_retries: How many times a failed outgoing delivery is retried.
    """

    url: str
    direction: WebhookDirection = WebhookDirection.OUTGOING
    event_filters: list[str] = Field(default_factory=lambda: ["*"])
    secret_ref: str = ""
    active: bool = True
    max_retries: int = 3

    def wants(self, topic: str) -> bool:
        """Return whether this subscription is interested in ``topic``."""
        from src.platform.integrations.events.bus import topic_matches

        return any(topic_matches(pattern, topic) for pattern in self.event_filters)


class WebhookDelivery(TenantScopedEntity):
    """A single (outgoing) webhook delivery attempt and its outcome."""

    subscription_id: str
    event_topic: str
    payload: dict[str, object] = Field(default_factory=dict)
    signature: str = ""
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempts: int = 0
    last_error: str = ""
    delivered_at: datetime | None = None


class InboundReceipt(TenantScopedEntity):
    """A record of a verified inbound webhook, retained for replay protection."""

    subscription_id: str
    signature: str
    event_topic: str = ""
    received_at: datetime | None = None
