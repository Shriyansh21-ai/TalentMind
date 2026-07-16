"""Notification framework models (Module 8).

A reusable, channel-agnostic notification model: templates, per-user
preferences, and notifications that move through a delivery lifecycle. Multiple
delivery channels (email, in-app, Slack, Teams, webhook, SMS, push) are
supported as *interfaces* — no provider is implemented here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from src.platform.common.models import PlatformModel, TenantScopedEntity


class Channel(str, Enum):
    """A notification delivery channel."""

    EMAIL = "email"
    IN_APP = "in_app"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"


class DeliveryStatus(str, Enum):
    """Lifecycle state of a notification."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    SUPPRESSED = "suppressed"  # blocked by preference


class DigestFrequency(str, Enum):
    """How often digest notifications are rolled up."""

    OFF = "off"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationTemplate(TenantScopedEntity):
    """A reusable subject/body template for a category + channel."""

    key: str
    channel: Channel = Channel.EMAIL
    subject_template: str = ""
    body_template: str = ""


class NotificationPreference(TenantScopedEntity):
    """A user's per-channel notification preferences."""

    user_id: str
    channels: dict[str, bool] = Field(default_factory=dict)
    digest_frequency: DigestFrequency = DigestFrequency.OFF

    def allows(self, channel: Channel) -> bool:
        """Return whether the user permits delivery on ``channel`` (default on)."""
        return bool(self.channels.get(channel.value, True))


class Notification(TenantScopedEntity):
    """A single notification instance destined for one recipient/channel."""

    recipient_id: str
    channel: Channel = Channel.IN_APP
    category: str = "general"
    subject: str = ""
    body: str = ""
    template_key: str | None = None
    status: DeliveryStatus = DeliveryStatus.PENDING
    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    error: str = ""


class DeliveryResult(PlatformModel):
    """The outcome of a channel delivery attempt."""

    channel: Channel
    ok: bool
    detail: str = ""
