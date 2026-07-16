"""Module 5 — Communication Providers.

Channels, templates and outbound messages, plus swappable provider interfaces
for Email, Slack, Microsoft Teams, Discord, SMS, WhatsApp Business and generic
Webhook notifications. Provider interfaces only — no API implementation.
"""

from __future__ import annotations

from src.platform.integrations.communication.models import (
    ChannelType,
    MessageChannel,
    MessageStatus,
    MessageTemplate,
    OutboundMessage,
)
from src.platform.integrations.communication.providers import (
    DiscordProvider,
    EmailProvider,
    SlackProvider,
    SmsProvider,
    TeamsProvider,
    WebhookNotificationProvider,
    WhatsAppProvider,
    all_providers,
)

__all__ = [
    "ChannelType",
    "MessageChannel",
    "MessageTemplate",
    "OutboundMessage",
    "MessageStatus",
    "EmailProvider",
    "SlackProvider",
    "TeamsProvider",
    "DiscordProvider",
    "SmsProvider",
    "WhatsAppProvider",
    "WebhookNotificationProvider",
    "all_providers",
]
