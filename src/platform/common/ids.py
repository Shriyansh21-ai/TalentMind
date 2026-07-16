"""Identifier generation and slug helpers.

Ids are prefixed so they are self-describing in logs and audit trails
(``org_3f2a…``, ``tnt_9b1c…``, ``usr_…``). Generation uses :mod:`uuid` which is
process-safe and requires no external state.
"""

from __future__ import annotations

import re
import uuid

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM = re.compile(r"(^-+|-+$)")


def generate_id(prefix: str) -> str:
    """Return a new globally-unique, prefixed identifier.

    Args:
        prefix: Short type tag, e.g. ``"org"``, ``"tnt"``, ``"usr"``.

    Returns:
        A string like ``"org_1f2e3d4c5b6a7089"`` (prefix + 16 hex chars).
    """
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def slugify(value: str) -> str:
    """Convert an arbitrary label into a url/dns-safe slug.

    Args:
        value: Human label, e.g. ``"Acme, Inc."``.

    Returns:
        Lower-kebab slug, e.g. ``"acme-inc"`` (empty string becomes ``"n-a"``).
    """
    lowered = value.strip().lower()
    slug = _SLUG_STRIP.sub("-", lowered)
    slug = _SLUG_TRIM.sub("", slug)
    return slug or "n-a"
