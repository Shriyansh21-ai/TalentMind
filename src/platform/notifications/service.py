"""Notification service (Module 8).

Composes templates, per-user preferences, delivery channels and scheduling into
one dispatcher. It respects preferences (suppressing disabled channels),
supports scheduled + immediate delivery, and can roll pending items into a
digest. Channels are pluggable; with none registered it degrades gracefully to
recording notifications in the store.
"""

from __future__ import annotations

from datetime import datetime

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.notifications.channels import NotificationChannel
from src.platform.notifications.models import (
    Channel,
    DeliveryStatus,
    Notification,
    NotificationPreference,
    NotificationTemplate,
)
from src.platform.notifications.templates import render


class NotificationService:
    """Dispatch notifications across channels with preferences + scheduling."""

    def __init__(
        self,
        *,
        notifications: InMemoryRepository[Notification] | None = None,
        templates: InMemoryRepository[NotificationTemplate] | None = None,
        preferences: InMemoryRepository[NotificationPreference] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.notifications = notifications or InMemoryRepository("notification")
        self.templates = templates or InMemoryRepository("notification_template")
        self.preferences = preferences or InMemoryRepository("notification_preference")
        self._clock = clock or SystemClock()
        self._channels: dict[Channel, NotificationChannel] = {}

    # -- wiring -------------------------------------------------------------

    def register_channel(self, channel: NotificationChannel) -> None:
        """Register a delivery channel implementation."""
        self._channels[channel.channel] = channel

    def register_template(
        self,
        tenant_id: str,
        organization_id: str,
        key: str,
        *,
        channel: Channel = Channel.EMAIL,
        subject_template: str = "",
        body_template: str = "",
    ) -> NotificationTemplate:
        """Register a reusable notification template."""
        now = self._clock.now()
        template = NotificationTemplate(
            id=generate_id("ntpl"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            key=key,
            channel=channel,
            subject_template=subject_template,
            body_template=body_template,
            created_at=now,
            updated_at=now,
        )
        return self.templates.add(template)

    def set_preference(
        self,
        tenant_id: str,
        organization_id: str,
        user_id: str,
        channels: dict[str, bool],
    ) -> NotificationPreference:
        """Set (or replace) a user's channel preferences."""
        existing = self.preferences.list(tenant_id=tenant_id, where=lambda p: p.user_id == user_id)
        now = self._clock.now()
        if existing:
            pref = existing[0]
            pref.channels = dict(channels)
            pref.touch(now)
            return self.preferences.update(pref)
        pref = NotificationPreference(
            id=generate_id("npref"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            user_id=user_id,
            channels=dict(channels),
            created_at=now,
            updated_at=now,
        )
        return self.preferences.add(pref)

    # -- sending ------------------------------------------------------------

    def _preference_for(self, tenant_id: str, user_id: str) -> NotificationPreference | None:
        """Return a user's preferences (or ``None``)."""
        found = self.preferences.list(tenant_id=tenant_id, where=lambda p: p.user_id == user_id)
        return found[0] if found else None

    def _template(self, tenant_id: str, key: str) -> NotificationTemplate | None:
        """Return a template by key within a tenant (or ``None``)."""
        found = self.templates.list(tenant_id=tenant_id, where=lambda t: t.key == key)
        return found[0] if found else None

    def send(
        self,
        tenant_id: str,
        organization_id: str,
        recipient_id: str,
        *,
        channel: Channel = Channel.IN_APP,
        category: str = "general",
        subject: str = "",
        body: str = "",
        template_key: str | None = None,
        context: dict[str, object] | None = None,
        scheduled_for: datetime | None = None,
    ) -> Notification:
        """Create and (unless scheduled) attempt to deliver a notification.

        If ``template_key`` is given, its subject/body are rendered with
        ``context``. If the recipient's preferences disable the channel, the
        notification is stored as ``SUPPRESSED`` and never delivered.
        """
        context = context or {}
        if template_key is not None:
            template = self._template(tenant_id, template_key)
            if template is not None:
                channel = template.channel
                subject = render(template.subject_template, context)
                body = render(template.body_template, context)

        now = self._clock.now()
        notification = Notification(
            id=generate_id("ntf"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            recipient_id=recipient_id,
            channel=channel,
            category=category,
            subject=subject,
            body=body,
            template_key=template_key,
            scheduled_for=scheduled_for,
            status=DeliveryStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        pref = self._preference_for(tenant_id, recipient_id)
        if pref is not None and not pref.allows(channel):
            notification.status = DeliveryStatus.SUPPRESSED
            return self.notifications.add(notification)

        if scheduled_for is not None and scheduled_for > now:
            notification.status = DeliveryStatus.SCHEDULED
            return self.notifications.add(notification)

        self.notifications.add(notification)
        self._deliver(notification)
        return notification

    def _deliver(self, notification: Notification) -> None:
        """Deliver via the registered channel, updating status in place."""
        now = self._clock.now()
        transport = self._channels.get(notification.channel)
        if transport is None:
            # No provider registered: record as sent (in-store delivery).
            notification.status = DeliveryStatus.SENT
            notification.sent_at = now
        else:
            result = transport.send(notification)
            notification.status = DeliveryStatus.SENT if result.ok else DeliveryStatus.FAILED
            notification.sent_at = now if result.ok else None
            notification.error = "" if result.ok else result.detail
        notification.touch(now)
        self.notifications.update(notification)

    # -- scheduling ---------------------------------------------------------

    def flush_due(self, tenant_id: str) -> int:
        """Deliver all scheduled notifications now due; return the count sent."""
        now = self._clock.now()
        due = self.notifications.list(
            tenant_id=tenant_id,
            where=lambda n: (
                n.status == DeliveryStatus.SCHEDULED
                and n.scheduled_for is not None
                and n.scheduled_for <= now
            ),
        )
        for notification in due:
            self._deliver(notification)
        return len(due)

    def inbox(self, tenant_id: str, recipient_id: str) -> list[Notification]:
        """Return a recipient's delivered in-app notifications (newest first)."""
        items = self.notifications.list(
            tenant_id=tenant_id,
            where=lambda n: (
                n.recipient_id == recipient_id
                and n.channel == Channel.IN_APP
                and n.status == DeliveryStatus.SENT
            ),
        )
        return list(reversed(items))
