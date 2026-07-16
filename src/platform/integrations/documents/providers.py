"""Document provider interfaces (Module 6).

Provider interfaces for Google Drive, OneDrive, SharePoint, Dropbox, Box,
Amazon S3 and Azure Blob Storage. Interfaces only — no connectors. Document
providers are bidirectional (read + write files) and support versioning where
the backend does.
"""

from __future__ import annotations

from src.platform.integrations.common.models import (
    AuthScheme,
    IntegrationCapabilities,
    IntegrationMetadata,
    ProviderCategory,
    SyncDirection,
)
from src.platform.integrations.common.provider import BaseIntegrationProvider

_DOC_ENTITIES = ["document", "folder", "version"]


def _doc_capabilities(*, webhooks: bool = False) -> IntegrationCapabilities:
    """Return a standard document capability profile (bidirectional)."""
    return IntegrationCapabilities(
        supports_read=True,
        supports_write=True,
        supports_full_sync=True,
        supports_incremental_sync=True,
        supports_webhooks=webhooks,
        supports_realtime=False,
        supports_bulk=True,
        direction=SyncDirection.BIDIRECTIONAL,
        entities=list(_DOC_ENTITIES),
        scopes=["files:read", "files:write"],
    )


class _DocumentProvider(BaseIntegrationProvider):
    """Base for document providers."""

    capabilities = _doc_capabilities()


class GoogleDriveProvider(_DocumentProvider):
    key = "google_drive"
    metadata = IntegrationMetadata(
        display_name="Google Drive",
        vendor="Google LLC",
        category=ProviderCategory.DOCUMENT,
        description="Google Drive document storage and sharing.",
        website="https://drive.google.com",
        logo_emoji="📁",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["storage", "google", "workspace"],
    )
    capabilities = _doc_capabilities(webhooks=True)


class OneDriveProvider(_DocumentProvider):
    key = "onedrive"
    metadata = IntegrationMetadata(
        display_name="OneDrive",
        vendor="Microsoft Corporation",
        category=ProviderCategory.DOCUMENT,
        description="Microsoft OneDrive personal and business file storage.",
        website="https://onedrive.live.com",
        logo_emoji="🗂️",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["storage", "microsoft", "m365"],
    )
    capabilities = _doc_capabilities(webhooks=True)


class SharePointProvider(_DocumentProvider):
    key = "sharepoint"
    metadata = IntegrationMetadata(
        display_name="SharePoint",
        vendor="Microsoft Corporation",
        category=ProviderCategory.DOCUMENT,
        description="Microsoft SharePoint document libraries and sites.",
        website="https://www.microsoft.com/microsoft-365/sharepoint",
        logo_emoji="📚",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["storage", "microsoft", "enterprise"],
    )


class DropboxProvider(_DocumentProvider):
    key = "dropbox"
    metadata = IntegrationMetadata(
        display_name="Dropbox",
        vendor="Dropbox, Inc.",
        category=ProviderCategory.DOCUMENT,
        description="Dropbox file storage and sharing.",
        website="https://www.dropbox.com",
        logo_emoji="📦",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["storage", "files"],
    )
    capabilities = _doc_capabilities(webhooks=True)


class BoxProvider(_DocumentProvider):
    key = "box"
    metadata = IntegrationMetadata(
        display_name="Box",
        vendor="Box, Inc.",
        category=ProviderCategory.DOCUMENT,
        description="Box enterprise content management.",
        website="https://www.box.com",
        logo_emoji="🅱️",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.SERVICE_ACCOUNT],
        tags=["storage", "enterprise", "ecm"],
    )


class AmazonS3Provider(_DocumentProvider):
    key = "amazon_s3"
    metadata = IntegrationMetadata(
        display_name="Amazon S3",
        vendor="Amazon Web Services, Inc.",
        category=ProviderCategory.DOCUMENT,
        description="Amazon S3 object storage buckets.",
        website="https://aws.amazon.com/s3/",
        logo_emoji="🪣",
        auth_schemes=[AuthScheme.SERVICE_ACCOUNT, AuthScheme.API_KEY],
        tags=["storage", "object", "aws"],
    )
    capabilities = _doc_capabilities()


class AzureBlobProvider(_DocumentProvider):
    key = "azure_blob"
    metadata = IntegrationMetadata(
        display_name="Azure Blob Storage",
        vendor="Microsoft Corporation",
        category=ProviderCategory.DOCUMENT,
        description="Azure Blob Storage containers.",
        website="https://azure.microsoft.com/products/storage/blobs/",
        logo_emoji="☁️",
        auth_schemes=[AuthScheme.SERVICE_ACCOUNT, AuthScheme.API_KEY],
        tags=["storage", "object", "azure"],
    )
    capabilities = _doc_capabilities()


def all_providers() -> list[BaseIntegrationProvider]:
    """Return one instance of every built-in document provider interface."""
    return [
        GoogleDriveProvider(),
        OneDriveProvider(),
        SharePointProvider(),
        DropboxProvider(),
        BoxProvider(),
        AmazonS3Provider(),
        AzureBlobProvider(),
    ]
