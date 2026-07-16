"""Communication provider interfaces (Module 5).

Provider interfaces for Email (SMTP/SendGrid-class), Slack, Microsoft Teams,
Discord, SMS, WhatsApp Business and generic Webhook notifications. Interfaces
only — no API implementation. Communication providers are outbound and often
support realtime delivery + templates.
"""

from __future__ import annotations

from src.platform.integrations.common.models import (
    AuthScheme,
    IntegrationCapabilities,
    IntegrationMetadata,
    ProviderCategory,
    SyncDirection,
)
from src.platform.integrations.common.provider import BaseIntegrationProvider


def _comm_capabilities(*, realtime: bool = True) -> IntegrationCapabilities:
    """Return a standard communication capability profile (outbound)."""
    return IntegrationCapabilities(
        supports_read=False,
        supports_write=True,
        supports_full_sync=False,
        supports_incremental_sync=False,
        supports_webhooks=True,
        supports_realtime=realtime,
        supports_bulk=True,
        direction=SyncDirection.OUTBOUND,
        entities=["message", "channel", "template"],
        scopes=["messages:send", "channels:read"],
    )


class _CommunicationProvider(BaseIntegrationProvider):
    """Base for communication providers."""

    capabilities = _comm_capabilities()


class EmailProvider(_CommunicationProvider):
    key = "email"
    metadata = IntegrationMetadata(
        display_name="Email (SMTP)",
        vendor="Generic",
        category=ProviderCategory.COMMUNICATION,
        description="Transactional email over SMTP or an email service provider.",
        logo_emoji="✉️",
        auth_schemes=[AuthScheme.BASIC, AuthScheme.API_KEY],
        tags=["email", "transactional"],
    )


class SlackProvider(_CommunicationProvider):
    key = "slack"
    metadata = IntegrationMetadata(
        display_name="Slack",
        vendor="Slack Technologies, LLC",
        category=ProviderCategory.COMMUNICATION,
        description="Slack channel and direct-message notifications.",
        website="https://slack.com",
        docs_url="https://api.slack.com",
        logo_emoji="💬",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.BEARER_TOKEN],
        tags=["chat", "collaboration"],
    )


class TeamsProvider(_CommunicationProvider):
    key = "microsoft_teams"
    metadata = IntegrationMetadata(
        display_name="Microsoft Teams",
        vendor="Microsoft Corporation",
        category=ProviderCategory.COMMUNICATION,
        description="Microsoft Teams channel messages and adaptive cards.",
        website="https://www.microsoft.com/microsoft-teams",
        logo_emoji="👥",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["chat", "collaboration", "m365"],
    )


class DiscordProvider(_CommunicationProvider):
    key = "discord"
    metadata = IntegrationMetadata(
        display_name="Discord",
        vendor="Discord Inc.",
        category=ProviderCategory.COMMUNICATION,
        description="Discord channel and webhook notifications.",
        website="https://discord.com",
        logo_emoji="🎮",
        auth_schemes=[AuthScheme.BEARER_TOKEN],
        tags=["chat", "community"],
    )


class SmsProvider(_CommunicationProvider):
    key = "sms"
    metadata = IntegrationMetadata(
        display_name="SMS",
        vendor="Generic (Twilio-class)",
        category=ProviderCategory.COMMUNICATION,
        description="SMS text messaging via a programmable messaging provider.",
        logo_emoji="📱",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.BASIC],
        tags=["sms", "text"],
    )


class WhatsAppProvider(_CommunicationProvider):
    key = "whatsapp"
    metadata = IntegrationMetadata(
        display_name="WhatsApp Business",
        vendor="Meta Platforms, Inc.",
        category=ProviderCategory.COMMUNICATION,
        description="WhatsApp Business messaging with approved templates.",
        website="https://business.whatsapp.com",
        logo_emoji="🟢",
        auth_schemes=[AuthScheme.BEARER_TOKEN, AuthScheme.API_KEY],
        tags=["messaging", "whatsapp"],
    )


class WebhookNotificationProvider(_CommunicationProvider):
    key = "webhook_notifications"
    metadata = IntegrationMetadata(
        display_name="Webhook Notifications",
        vendor="Generic",
        category=ProviderCategory.COMMUNICATION,
        description="Generic outbound HTTP webhook notification channel.",
        logo_emoji="🪝",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.NONE],
        tags=["webhook", "http"],
    )


def all_providers() -> list[BaseIntegrationProvider]:
    """Return one instance of every built-in communication provider interface."""
    return [
        EmailProvider(),
        SlackProvider(),
        TeamsProvider(),
        DiscordProvider(),
        SmsProvider(),
        WhatsAppProvider(),
        WebhookNotificationProvider(),
    ]
