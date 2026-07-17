"""Lazy dependency-injection container (Module 14).

A tiny, explicit service locator that supports constructor injection without a
third-party framework. Providers are registered as zero-arg factories and are
instantiated **lazily** on first resolution; singletons are memoised so
expensive graphs (repositories, caches, services) are built at most once.

This is the composition mechanism; the platform composition root that wires the
concrete services together lives in :mod:`src.platform.bootstrap`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.platform.common.errors import ConfigurationError

T = TypeVar("T")


class Container:
    """A minimal lazy DI container.

    Register providers with :meth:`register` (singleton) or
    :meth:`register_factory` (new instance per resolve), then obtain wired
    services with :meth:`resolve`.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[Container], object]] = {}
        self._singletons: dict[str, bool] = {}
        self._instances: dict[str, object] = {}

    def register(
        self, key: str, provider: Callable[[Container], T], *, singleton: bool = True
    ) -> None:
        """Register ``provider`` under ``key``.

        Args:
            key: Lookup name (e.g. ``"organizations"``).
            provider: Callable taking the container and returning the service.
                Receiving the container lets a provider resolve its own deps.
            singleton: If ``True`` (default) the instance is memoised.
        """
        self._factories[key] = provider  # type: ignore[assignment]
        self._singletons[key] = singleton
        self._instances.pop(key, None)

    def register_instance(self, key: str, instance: T) -> None:
        """Register an already-constructed ``instance`` as an eager singleton."""
        self._factories[key] = lambda _c: instance
        self._singletons[key] = True
        self._instances[key] = instance

    def has(self, key: str) -> bool:
        """Return whether ``key`` has a registered provider."""
        return key in self._factories

    def resolve(self, key: str) -> object:
        """Instantiate (lazily) and return the service registered under ``key``."""
        if key not in self._factories:
            raise ConfigurationError(f"no provider registered for '{key}'")
        if self._singletons.get(key) and key in self._instances:
            return self._instances[key]
        instance = self._factories[key](self)
        if self._singletons.get(key):
            self._instances[key] = instance
        return instance

    def keys(self) -> list[str]:
        """Return all registered provider keys (registration order)."""
        return list(self._factories)

    def reset(self) -> None:
        """Drop all memoised singleton instances (keeps registrations)."""
        self._instances.clear()
