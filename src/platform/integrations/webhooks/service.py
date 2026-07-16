"""Webhook service (Module 8).

The application service that ties the webhook models, signer and secret vault
together: register outgoing/incoming subscriptions, dispatch signed outgoing
deliveries with bounded retries and a dead-letter queue, and verify inbound
deliveries with signature + replay protection. Delivery is performed through an
injectable transport so the platform stays offline by default; tests inject a
transport that can succeed or fail deterministically.
"""

from __future__ import annotations

import json
from typing import Callable

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.integrations.common.errors import WebhookVerificationError
from src.platform.integrations.common.secrets import CredentialType, CredentialVault
from src.platform.integrations.webhooks.models import (
    DeliveryStatus,
    InboundReceipt,
    WebhookDelivery,
    WebhookDirection,
    WebhookSubscription,
)
from src.platform.integrations.webhooks.signing import WebhookSigner

#: A transport delivers a signed payload: ``(url, headers, body) -> ok``.
WebhookTransport = Callable[[str, dict, str], bool]


def _always_ok(url: str, headers: dict, body: str) -> bool:
    """Default offline transport — records intent to deliver, always succeeds."""
    return True


def _canonical_body(payload: dict[str, object]) -> str:
    """Serialize a payload deterministically (stable key order)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class WebhookService:
    """Register, sign, deliver and verify webhooks (tenant-isolated)."""

    def __init__(
        self,
        *,
        vault: CredentialVault | None = None,
        signer: WebhookSigner | None = None,
        transport: WebhookTransport | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._clock = clock or SystemClock()
        self.vault = vault or CredentialVault(clock=self._clock)
        self.signer = signer or WebhookSigner(clock=self._clock)
        self._transport = transport or _always_ok
        self.subscriptions_repo: InMemoryRepository[WebhookSubscription] = (
            InMemoryRepository("webhook_subscription")
        )
        self.deliveries_repo: InMemoryRepository[WebhookDelivery] = InMemoryRepository(
            "webhook_delivery"
        )
        self.receipts_repo: InMemoryRepository[InboundReceipt] = InMemoryRepository(
            "webhook_receipt"
        )

    # -- registration -------------------------------------------------------

    def register(
        self,
        tenant_id: str,
        organization_id: str,
        url: str,
        *,
        secret: str,
        direction: WebhookDirection = WebhookDirection.OUTGOING,
        event_filters: list[str] | None = None,
        max_retries: int = 3,
    ) -> WebhookSubscription:
        """Register a webhook subscription and store its signing secret."""
        ref = self.vault.issue(
            tenant_id, secret, credential_type=CredentialType.API_KEY
        )
        now = self._clock.now()
        subscription = WebhookSubscription(
            id=generate_id("whk"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            url=url,
            direction=direction,
            event_filters=event_filters or ["*"],
            secret_ref=ref.ref,
            max_retries=max_retries,
            created_at=now,
            updated_at=now,
        )
        return self.subscriptions_repo.add(subscription)

    def subscriptions(
        self, tenant_id: str, *, direction: WebhookDirection | None = None
    ) -> list[WebhookSubscription]:
        """Return a tenant's webhook subscriptions, optionally by direction."""
        where = None
        if direction is not None:
            where = lambda s: s.direction == direction  # noqa: E731
        return self.subscriptions_repo.list(tenant_id=tenant_id, where=where)

    # -- outgoing -----------------------------------------------------------

    def dispatch(
        self, tenant_id: str, topic: str, payload: dict[str, object]
    ) -> list[WebhookDelivery]:
        """Deliver ``topic`` to every matching, active outgoing subscription."""
        results: list[WebhookDelivery] = []
        for sub in self.subscriptions(tenant_id, direction=WebhookDirection.OUTGOING):
            if not sub.active or not sub.wants(topic):
                continue
            results.append(self._deliver(sub, topic, payload))
        return results

    def _deliver(
        self, sub: WebhookSubscription, topic: str, payload: dict[str, object]
    ) -> WebhookDelivery:
        body = _canonical_body(payload)
        secret = self.vault.resolve(sub.tenant_id, sub.secret_ref)
        signature = self.signer.sign(secret, body)
        now = self._clock.now()
        delivery = WebhookDelivery(
            id=generate_id("whd"),
            tenant_id=sub.tenant_id,
            organization_id=sub.organization_id,
            subscription_id=sub.id,
            event_topic=topic,
            payload=payload,
            signature=signature,
            created_at=now,
            updated_at=now,
        )
        self.deliveries_repo.add(delivery)
        self._attempt(delivery, sub, body, signature)
        return delivery

    def _attempt(
        self,
        delivery: WebhookDelivery,
        sub: WebhookSubscription,
        body: str,
        signature: str,
    ) -> None:
        headers = {
            "Content-Type": "application/json",
            "X-TalentMind-Topic": delivery.event_topic,
            "X-TalentMind-Signature": signature,
        }
        # One initial attempt plus up to max_retries retries.
        for _ in range(sub.max_retries + 1):
            delivery.attempts += 1
            try:
                ok = self._transport(sub.url, headers, body)
            except Exception as exc:  # transport error counts as a failure
                ok = False
                delivery.last_error = str(exc)
            if ok:
                delivery.status = DeliveryStatus.DELIVERED
                delivery.delivered_at = self._clock.now()
                delivery.last_error = ""
                self.deliveries_repo.update(delivery)
                return
            delivery.status = DeliveryStatus.FAILED
        delivery.status = DeliveryStatus.DEAD_LETTERED
        if not delivery.last_error:
            delivery.last_error = "delivery failed after retries"
        self.deliveries_repo.update(delivery)

    def retry(self, tenant_id: str, delivery_id: str) -> WebhookDelivery:
        """Re-attempt a failed/dead-lettered delivery."""
        delivery = self.deliveries_repo.require(delivery_id, tenant_id=tenant_id)
        sub = self.subscriptions_repo.require(
            delivery.subscription_id, tenant_id=tenant_id
        )
        body = _canonical_body(delivery.payload)
        secret = self.vault.resolve(tenant_id, sub.secret_ref)
        signature = self.signer.sign(secret, body)
        delivery.signature = signature
        self._attempt(delivery, sub, body, signature)
        return delivery

    def deliveries(
        self, tenant_id: str, *, status: DeliveryStatus | None = None
    ) -> list[WebhookDelivery]:
        """Return a tenant's delivery history, optionally by status."""
        where = None
        if status is not None:
            where = lambda d: d.status == status  # noqa: E731
        return self.deliveries_repo.list(tenant_id=tenant_id, where=where)

    def dead_letters(self, tenant_id: str) -> list[WebhookDelivery]:
        """Return the tenant's dead-lettered deliveries."""
        return self.deliveries(tenant_id, status=DeliveryStatus.DEAD_LETTERED)

    # -- incoming -----------------------------------------------------------

    def receive(
        self,
        tenant_id: str,
        subscription_id: str,
        payload: dict[str, object],
        signature: str,
        *,
        topic: str = "",
    ) -> InboundReceipt:
        """Verify an inbound webhook and record a replay-protected receipt.

        Raises:
            WebhookVerificationError: If the signature is invalid, stale or a
                replay of a previously-accepted signature.
        """
        sub = self.subscriptions_repo.require(subscription_id, tenant_id=tenant_id)
        if sub.direction != WebhookDirection.INCOMING:
            raise WebhookVerificationError("subscription is not an incoming webhook")
        body = _canonical_body(payload)
        secret = self.vault.resolve(tenant_id, sub.secret_ref)
        self.signer.verify(secret, body, signature)  # raises on failure
        now = self._clock.now()
        receipt = InboundReceipt(
            id=generate_id("whr"),
            tenant_id=tenant_id,
            organization_id=sub.organization_id,
            subscription_id=subscription_id,
            signature=signature,
            event_topic=topic,
            received_at=now,
            created_at=now,
            updated_at=now,
        )
        return self.receipts_repo.add(receipt)
