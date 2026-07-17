"""Module 8 tests — Webhook platform.

Exercises HMAC signing/verification, replay protection and the freshness
window, outgoing delivery with bounded retries and dead-lettering, and inbound
verification — all offline through an injectable transport.
"""

from __future__ import annotations

import pytest

from src.platform.common.clock import FrozenClock
from src.platform.integrations.common.errors import WebhookVerificationError
from src.platform.integrations.webhooks import (
    DeliveryStatus,
    WebhookDirection,
    WebhookService,
    WebhookSigner,
)

# -- signing ----------------------------------------------------------------


def test_sign_and_verify_roundtrip():
    signer = WebhookSigner(clock=FrozenClock())
    signature = signer.sign("secret", '{"a":1}')
    assert signer.verify("secret", '{"a":1}', signature)


def test_tampered_payload_fails_verification():
    signer = WebhookSigner(clock=FrozenClock())
    signature = signer.sign("secret", '{"a":1}')
    with pytest.raises(WebhookVerificationError):
        signer.verify("secret", '{"a":2}', signature)


def test_replay_is_rejected():
    signer = WebhookSigner(clock=FrozenClock())
    signature = signer.sign("secret", "body")
    assert signer.verify("secret", "body", signature)
    with pytest.raises(WebhookVerificationError):
        signer.verify("secret", "body", signature)


def test_stale_signature_outside_tolerance_rejected():
    clock = FrozenClock()
    signer = WebhookSigner(clock=clock, tolerance_seconds=300)
    signature = signer.sign("secret", "body")
    clock.advance(seconds=301)
    with pytest.raises(WebhookVerificationError):
        signer.verify("secret", "body", signature)


# -- outgoing delivery ------------------------------------------------------


def test_outgoing_delivery_succeeds():
    service = WebhookService(clock=FrozenClock())
    service.register("t1", "o1", "https://x/hook", secret="s", event_filters=["a.*"])
    deliveries = service.dispatch("t1", "a.created", {"x": 1})
    assert len(deliveries) == 1
    assert deliveries[0].status == DeliveryStatus.DELIVERED


def test_delivery_filter_excludes_non_matching_topics():
    service = WebhookService(clock=FrozenClock())
    service.register("t1", "o1", "https://x/hook", secret="s", event_filters=["a.*"])
    assert service.dispatch("t1", "b.created", {"x": 1}) == []


def test_failed_delivery_dead_letters_after_retries():
    calls = {"n": 0}

    def failing_transport(url, headers, body):
        calls["n"] += 1
        return False

    service = WebhookService(transport=failing_transport, clock=FrozenClock())
    service.register("t1", "o1", "https://x/hook", secret="s", event_filters=["*"], max_retries=2)
    deliveries = service.dispatch("t1", "a.created", {"x": 1})
    delivery = deliveries[0]
    assert delivery.status == DeliveryStatus.DEAD_LETTERED
    assert delivery.attempts == 3  # 1 initial + 2 retries
    assert calls["n"] == 3
    assert service.dead_letters("t1") == [delivery]


def test_retry_recovers_a_dead_letter():
    state = {"fail": True}

    def flaky_transport(url, headers, body):
        return not state["fail"]

    service = WebhookService(transport=flaky_transport, clock=FrozenClock())
    service.register("t1", "o1", "https://x/hook", secret="s", max_retries=0)
    delivery = service.dispatch("t1", "a.created", {"x": 1})[0]
    assert delivery.status == DeliveryStatus.DEAD_LETTERED
    state["fail"] = False
    retried = service.retry("t1", delivery.id)
    assert retried.status == DeliveryStatus.DELIVERED


# -- incoming ---------------------------------------------------------------


def test_incoming_verification_accepts_valid_signature():
    clock = FrozenClock()
    service = WebhookService(clock=clock)
    sub = service.register(
        "t1",
        "o1",
        "https://src/in",
        secret="insecret",
        direction=WebhookDirection.INCOMING,
    )
    secret = service.vault.resolve("t1", sub.secret_ref)
    body = '{"event":"ping"}'  # must match canonical serialization
    import json

    payload = {"event": "ping"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    signature = service.signer.sign(secret, canonical)
    receipt = service.receive("t1", sub.id, payload, signature, topic="ping")
    assert receipt.subscription_id == sub.id


def test_incoming_rejects_bad_signature():
    service = WebhookService(clock=FrozenClock())
    sub = service.register(
        "t1",
        "o1",
        "https://src/in",
        secret="insecret",
        direction=WebhookDirection.INCOMING,
    )
    with pytest.raises(WebhookVerificationError):
        service.receive("t1", sub.id, {"event": "ping"}, "t=1,v1=deadbeef")
