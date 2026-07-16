"""Module 8 — Webhook Platform.

Outgoing and incoming webhooks with real HMAC-SHA256 signing, verification,
replay protection, bounded retries, delivery history and a dead-letter queue.
Delivery uses an injectable transport so the platform stays offline by default.
"""

from __future__ import annotations

from src.platform.integrations.webhooks.models import (
    DeliveryStatus,
    InboundReceipt,
    WebhookDelivery,
    WebhookDirection,
    WebhookSubscription,
)
from src.platform.integrations.webhooks.service import (
    WebhookService,
    WebhookTransport,
)
from src.platform.integrations.webhooks.signing import (
    DEFAULT_TOLERANCE_SECONDS,
    WebhookSigner,
)

__all__ = [
    "WebhookDirection",
    "DeliveryStatus",
    "WebhookSubscription",
    "WebhookDelivery",
    "InboundReceipt",
    "WebhookSigner",
    "DEFAULT_TOLERANCE_SECONDS",
    "WebhookService",
    "WebhookTransport",
]
