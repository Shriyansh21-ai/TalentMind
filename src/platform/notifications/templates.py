"""Notification templating (Module 8).

A tiny, safe renderer over ``str.format_map`` that leaves unknown placeholders
intact rather than raising, so a partially-populated context never crashes a
notification. Templates themselves are stored as
:class:`~src.platform.notifications.models.NotificationTemplate` entities.
"""

from __future__ import annotations


class _SafeDict(dict):
    """A dict that renders missing keys as ``{key}`` instead of raising."""

    def __missing__(self, key: str) -> str:  # noqa: D401
        return "{" + key + "}"


def render(template: str, context: dict[str, object]) -> str:
    """Render ``template`` against ``context``, tolerating missing keys."""
    return template.format_map(_SafeDict(context))
