"""Document integration models (Module 6).

Document metadata, versioning and a storage abstraction for the document
provider family (Google Drive, OneDrive, SharePoint, Dropbox, Box, S3, Azure
Blob). Metadata and version records are tenant-scoped; the storage seam is a
thin, provider-agnostic reference. **No connectors are implemented** — the
actual bytes remain behind a
:class:`~src.platform.storage.providers.StorageProvider`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from src.platform.common.models import Metadata, PlatformModel, TenantScopedEntity


class DocumentKind(str, Enum):
    """The kind of document being referenced."""

    RESUME = "resume"
    OFFER_LETTER = "offer_letter"
    CONTRACT = "contract"
    REPORT = "report"
    ATTACHMENT = "attachment"
    OTHER = "other"


class DocumentVersion(PlatformModel):
    """A single immutable version of a document."""

    version: int = 1
    checksum: str = ""
    size_bytes: int = 0
    author_id: str = ""
    note: str = ""


class DocumentMetadata(TenantScopedEntity):
    """Tenant-scoped catalogue metadata for a document held in a provider.

    Tracks the logical document (name, kind, folder path, current version) and
    its version history. The bytes themselves are addressed by ``storage_key``
    within the backing storage provider, never stored here.
    """

    integration_id: str = ""
    name: str
    kind: DocumentKind = DocumentKind.OTHER
    content_type: str = "application/octet-stream"
    folder_path: str = "/"
    storage_key: str = ""
    current_version: int = 1
    versions: list[DocumentVersion] = Field(default_factory=list)
    metadata: Metadata = Field(default_factory=Metadata)

    def add_version(
        self, *, checksum: str = "", size_bytes: int = 0, author_id: str = "", note: str = ""
    ) -> DocumentVersion:
        """Append a new version and advance ``current_version``."""
        next_version = (self.versions[-1].version + 1) if self.versions else 1
        version = DocumentVersion(
            version=next_version,
            checksum=checksum,
            size_bytes=size_bytes,
            author_id=author_id,
            note=note,
        )
        self.versions.append(version)
        self.current_version = next_version
        return version


class StorageAbstraction(PlatformModel):
    """A provider-agnostic description of where a document namespace lives.

    Lets the platform reason about "which bucket / drive / site" a tenant's
    documents map to, independent of the concrete provider. Purely descriptive.
    """

    provider_key: str
    root: str = "/"
    region: str = ""
    bucket: str = ""

    def resolve_key(self, tenant_id: str, relative_key: str) -> str:
        """Return a fully-qualified, tenant-namespaced storage key."""
        cleaned = relative_key.lstrip("/")
        return f"{self.root.rstrip('/')}/t/{tenant_id}/{cleaned}"
