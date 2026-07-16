"""Module 8 — Notification Framework.

A reusable, channel-agnostic notification architecture: templates, per-user
preferences, scheduling/digests and a pluggable :class:`NotificationChannel`
seam covering email, in-app, Slack, Teams, webhook, SMS and push. No network
provider is implemented — only interfaces plus offline test doubles.
"""

from __future__ import annotations

from src.platform.notifications.channels import (
    InMemoryChannel,
    NotificationChannel,
    NullChannel,
)
from src.platform.notifications.models import (
    Channel,
    DeliveryResult,
    DeliveryStatus,
    DigestFrequency,
    Notification,
    NotificationPreference,
    NotificationTemplate,
)
from src.platform.notifications.service import NotificationService
from src.platform.notifications.templates import render

__all__ = [
    "Channel",
    "DeliveryStatus",
    "DigestFrequency",
    "DeliveryResult",
    "Notification",
    "NotificationTemplate",
    "NotificationPreference",
    "NotificationChannel",
    "NullChannel",
    "InMemoryChannel",
    "NotificationService",
    "render",
]
