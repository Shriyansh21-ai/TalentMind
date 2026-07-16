"""Module 12 — Developer SDK Foundation.

Declarative descriptors for the planned Python, JavaScript, REST-client,
webhook, plugin, authentication and extension SDKs, plus an offline
:class:`RestClientFoundation` that speaks the standard API envelope in-process.
Future package structure only — no SDK is published.
"""

from __future__ import annotations

from src.platform.integrations.sdk.foundation import (
    RestClientFoundation,
    SdkDefinition,
    SdkKind,
    sdk_catalog,
)

__all__ = [
    "SdkKind",
    "SdkDefinition",
    "sdk_catalog",
    "RestClientFoundation",
]
