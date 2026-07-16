"""Module 11 — Storage Architecture.

Provider abstractions for document/object/blob/archive/vector/temporary storage
and a CDN URL surface, with tenant-namespaced in-memory reference providers.
Interfaces only — no cloud integration.
"""

from __future__ import annotations

from src.platform.storage.models import StorageClass, StoredObject
from src.platform.storage.providers import (
    InMemoryStorageProvider,
    InMemoryVectorStore,
    StorageProvider,
    VectorStore,
)
from src.platform.storage.service import StorageService

__all__ = [
    "StorageClass",
    "StoredObject",
    "StorageProvider",
    "InMemoryStorageProvider",
    "VectorStore",
    "InMemoryVectorStore",
    "StorageService",
]
