"""Deterministic composer registry for the offline (``local``) provider.

A *composer* maps a structured evidence dict to a schema-shaped response dict,
purely by restating and organizing the evidence — it never invents facts. Agents
register a composer for their output schema at import time; the
:class:`LocalHeuristicProvider` looks one up by schema name.

This is what makes the platform work with **zero external dependencies** while
still flowing through the real provider interface, and it is the backbone of the
Safety guarantee: in offline mode a response is a deterministic function of the
deterministic engines' output, so hallucination is structurally impossible.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

Composer = Callable[[Dict[str, Any]], Dict[str, Any]]

_COMPOSERS: Dict[str, Composer] = {}


def register_composer(schema_name: str, composer: Composer) -> None:
    """Register ``composer`` as the deterministic builder for ``schema_name``."""
    _COMPOSERS[schema_name] = composer


def get_composer(schema_name: str) -> Composer | None:
    """Return the composer registered for ``schema_name`` (or ``None``)."""
    return _COMPOSERS.get(schema_name)


def has_composer(schema_name: str) -> bool:
    """Return ``True`` iff a composer is registered for ``schema_name``."""
    return schema_name in _COMPOSERS
