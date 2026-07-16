"""Notification channels (Module 8) — interfaces + offline test doubles.

Defines the :class:`NotificationChannel` seam every real provider (SendGrid,
Slack, Twilio, …) must satisfy. Ships only offline doubles: :class:`NullChannel`
(drops) and :class:`InMemoryChannel` (captures for inspection/tests). No network
provider is implemented — that is a future integration.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.notifications.models import (
    Channel,
    DeliveryResult,
    Notification,
)


@runtime_checkable
class NotificationChannel(Protocol):
    """A transport capable of delivering a notification on one channel."""

    channel: Channel

    def send(self, notification: Notification) -> DeliveryResult:
        """Attempt delivery and return a :class:`DeliveryResult`."""
        ...


class NullChannel:
    """A channel that accepts and silently drops notifications."""

    def __init__(self, channel: Channel) -> None:
        self.channel = channel

    def send(self, notification: Notification) -> DeliveryResult:
        """Report success without doing anything."""
        return DeliveryResult(channel=self.channel, ok=True, detail="dropped (null)")


class InMemoryChannel:
    """A channel that records delivered notifications (for tests/preview)."""

    def __init__(self, channel: Channel) -> None:
        self.channel = channel
        self.outbox: list[Notification] = []

    def send(self, notification: Notification) -> DeliveryResult:
        """Capture the notification and report success."""
        self.outbox.append(notification)
        return DeliveryResult(channel=self.channel, ok=True, detail="captured")
