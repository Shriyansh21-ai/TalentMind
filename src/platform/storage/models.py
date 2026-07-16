"""Storage architecture models (Module 11).

Metadata describing stored artifacts across storage classes (document, object,
blob, archive, vector, temporary). The bytes live behind a
:class:`~src.platform.storage.providers.StorageProvider`; these models are the
tenant-scoped catalogue the platform reasons about.
"""

from __future__ import annotations

from enum import Enum

from src.platform.common.models import Metadata, TenantScopedEntity
from pydantic import Field


class StorageClass(str, Enum):
    """The class of storage an object lives in."""

    DOCUMENT = "document"
    OBJECT = "object"
    BLOB = "blob"
    ARCHIVE = "archive"
    VECTOR = "vector"
    TEMPORARY = "temporary"


class StoredObject(TenantScopedEntity):
    """Catalogue metadata for a stored artifact (not the bytes themselves)."""

    key: str
    storage_class: StorageClass = StorageClass.OBJECT
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    checksum: str = ""
    cdn_url: str = ""
    metadata: Metadata = Field(default_factory=Metadata)
