"""Communication integration models (Module 5).

Channels, message templates and outbound messages for the communication
provider family (email, Slack, Teams, Discord, SMS, WhatsApp, webhook). Pure
domain models with a tiny, safe template renderer — **no provider is
implemented**. A production communication connector consumes these models behind
the provider seam.
"""

from __future__ import annotations

from enum import Enum
from string import Template

from pydantic import Field

from src.platform.common.models import Metadata, PlatformModel, TenantScopedEntity


class ChannelType(str, Enum):
    """The transport a communication channel uses."""

    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"


class MessageStatus(str, Enum):
    """Delivery lifecycle of an outbound message."""

    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class MessageChannel(TenantScopedEntity):
    """A tenant-scoped, named delivery channel bound to a provider."""

    name: str
    channel_type: ChannelType = ChannelType.EMAIL
    integration_id: str = ""
    target: str = ""  # address / channel-id / phone / webhook url (non-secret)
    enabled: bool = True
    metadata: Metadata = Field(default_factory=Metadata)


class MessageTemplate(TenantScopedEntity):
    """A reusable, variable-substituting message template.

    Rendering uses :class:`string.Template` (``$var`` / ``${var}``) which is
    safe — it performs no code evaluation and leaves unknown placeholders intact.
    """

    key: str
    subject: str = ""
    body: str = ""
    channel_type: ChannelType = ChannelType.EMAIL
    variables: list[str] = Field(default_factory=list)

    def render(self, context: dict[str, object]) -> tuple[str, str]:
        """Return ``(subject, body)`` with ``$variables`` substituted safely."""
        safe = {k: str(v) for k, v in context.items()}
        subject = Template(self.subject).safe_substitute(safe)
        body = Template(self.body).safe_substitute(safe)
        return subject, body


class OutboundMessage(TenantScopedEntity):
    """A rendered message queued for (simulated) delivery over a channel."""

    channel_id: str
    channel_type: ChannelType = ChannelType.EMAIL
    template_key: str = ""
    subject: str = ""
    body: str = ""
    recipients: list[str] = Field(default_factory=list)
    status: MessageStatus = MessageStatus.DRAFT
    metadata: Metadata = Field(default_factory=Metadata)
