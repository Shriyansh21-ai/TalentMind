"""Module 6 — Document Providers.

Document metadata, versioning and a storage abstraction, plus swappable provider
interfaces for Google Drive, OneDrive, SharePoint, Dropbox, Box, Amazon S3 and
Azure Blob Storage. No connectors — interfaces and models only.
"""

from __future__ import annotations

from src.platform.integrations.documents.models import (
    DocumentKind,
    DocumentMetadata,
    DocumentVersion,
    StorageAbstraction,
)
from src.platform.integrations.documents.providers import (
    AmazonS3Provider,
    AzureBlobProvider,
    BoxProvider,
    DropboxProvider,
    GoogleDriveProvider,
    OneDriveProvider,
    SharePointProvider,
    all_providers,
)

__all__ = [
    "DocumentKind",
    "DocumentMetadata",
    "DocumentVersion",
    "StorageAbstraction",
    "GoogleDriveProvider",
    "OneDriveProvider",
    "SharePointProvider",
    "DropboxProvider",
    "BoxProvider",
    "AmazonS3Provider",
    "AzureBlobProvider",
    "all_providers",
]
