"""Hook registry (Module 12).

Named extension points. Two flavours, following the familiar plugin idiom:

* **filter hooks** transform a value through an ordered chain of callbacks
  (each receives the running value and returns a possibly-modified value);
* **action hooks** fire side effects and their return values are collected.

Extensions register callbacks against hook names; the platform triggers them at
well-defined points. Ordering is by ascending ``priority``.
"""

from __future__ import annotations

from typing import Any, Callable


class HookRegistry:
    """A registry of prioritised filter/action hook callbacks."""

    def __init__(self) -> None:
        # hook name -> list of (priority, callback)
        self._hooks: dict[str, list[tuple[int, Callable[..., Any]]]] = {}

    def add(self, name: str, callback: Callable[..., Any], *, priority: int = 10) -> None:
        """Register ``callback`` under hook ``name`` at ``priority`` (lower first)."""
        self._hooks.setdefault(name, []).append((priority, callback))
        self._hooks[name].sort(key=lambda pair: pair[0])

    def has(self, name: str) -> bool:
        """Return whether any callback is registered for ``name``."""
        return bool(self._hooks.get(name))

    def apply_filters(self, name: str, value: Any, **context: Any) -> Any:
        """Thread ``value`` through every callback for ``name`` and return it."""
        for _priority, callback in self._hooks.get(name, []):
            value = callback(value, **context)
        return value

    def do_action(self, name: str, **context: Any) -> list[Any]:
        """Invoke every callback for ``name`` for effect; collect return values."""
        return [cb(**context) for _priority, cb in self._hooks.get(name, [])]
