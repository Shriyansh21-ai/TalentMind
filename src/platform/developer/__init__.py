"""Module 12 — Developer Platform.

A plugin/extension framework: an error-isolating :class:`EventBus`, a
prioritised :class:`HookRegistry` (filter + action hooks), a declarative
plugin/manifest model with lifecycle management via :class:`ExtensionRegistry`,
a narrow :class:`PlatformSDK` capability surface, and a marketplace catalogue
stub. Framework only — no plugins ship.
"""

from __future__ import annotations

from src.platform.developer.events import Event, EventBus, EventResult
from src.platform.developer.hooks import HookRegistry
from src.platform.developer.plugins import (
    ExtensionRegistry,
    Marketplace,
    Plugin,
    PluginManifest,
    RegisteredPlugin,
)
from src.platform.developer.sdk import PlatformSDK

__all__ = [
    "Event",
    "EventBus",
    "EventResult",
    "HookRegistry",
    "Plugin",
    "PluginManifest",
    "RegisteredPlugin",
    "ExtensionRegistry",
    "Marketplace",
    "PlatformSDK",
]
