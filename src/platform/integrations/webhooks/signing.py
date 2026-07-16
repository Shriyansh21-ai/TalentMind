"""Webhook signing, verification & replay protection (Module 8 · Module 14).

Real HMAC-SHA256 signing over a canonical ``timestamp.payload`` string — the
same scheme Stripe/GitHub-style webhooks use — with constant-time comparison,
a freshness window to defeat replay of stale requests, and a per-signature seen
set to defeat replay of captured-but-fresh requests.

This is genuine cryptography (stdlib :mod:`hmac`/:mod:`hashlib`); no network I/O
is performed. Secrets are supplied by the caller (resolved from the
:class:`~src.platform.integrations.common.secrets.CredentialVault`) and never
logged.
"""

from __future__ import annotations

import hashlib
import hmac

from src.platform.common.clock import Clock, SystemClock
from src.platform.integrations.common.errors import WebhookVerificationError

#: Default freshness window for inbound signatures (seconds).
DEFAULT_TOLERANCE_SECONDS = 300


def _canonical(timestamp: int, payload: str) -> bytes:
    """Return the canonical bytes signed: ``"<timestamp>.<payload>"``."""
    return f"{timestamp}.{payload}".encode("utf-8")


class WebhookSigner:
    """Signs outgoing payloads and verifies inbound ones (with replay guard)."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
    ) -> None:
        self._clock = clock or SystemClock()
        self._tolerance = tolerance_seconds
        self._seen: set[str] = set()

    def sign(self, secret: str, payload: str, *, timestamp: int | None = None) -> str:
        """Return a signature header value ``"t=<ts>,v1=<hex>"``."""
        ts = timestamp if timestamp is not None else int(self._clock.now().timestamp())
        digest = hmac.new(
            secret.encode("utf-8"), _canonical(ts, payload), hashlib.sha256
        ).hexdigest()
        return f"t={ts},v1={digest}"

    def _parse(self, signature: str) -> tuple[int, str]:
        parts = dict(
            piece.split("=", 1) for piece in signature.split(",") if "=" in piece
        )
        if "t" not in parts or "v1" not in parts:
            raise WebhookVerificationError("malformed signature header")
        try:
            return int(parts["t"]), parts["v1"]
        except ValueError as exc:
            raise WebhookVerificationError("invalid signature timestamp") from exc

    def verify(
        self,
        secret: str,
        payload: str,
        signature: str,
        *,
        enforce_replay_protection: bool = True,
    ) -> bool:
        """Verify a signature, or raise :class:`WebhookVerificationError`.

        Checks, in order: header shape, freshness (within the tolerance
        window), the HMAC digest (constant-time), and — if
        ``enforce_replay_protection`` — that this exact signature has not been
        accepted before.
        """
        ts, provided = self._parse(signature)
        now = int(self._clock.now().timestamp())
        if abs(now - ts) > self._tolerance:
            raise WebhookVerificationError("signature timestamp outside tolerance window")

        expected = hmac.new(
            secret.encode("utf-8"), _canonical(ts, payload), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, provided):
            raise WebhookVerificationError("signature mismatch")

        if enforce_replay_protection:
            if provided in self._seen:
                raise WebhookVerificationError("replayed signature rejected")
            self._seen.add(provided)
        return True
