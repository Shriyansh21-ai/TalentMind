"""Storage service (Module 11).

Routes each storage class to a provider, records tenant-scoped catalogue
metadata for every stored artifact, and exposes CDN URLs. Providers are
pluggable; by default every class maps to a shared in-memory provider so the
platform works fully offline.
"""

from __future__ import annotations

import hashlib

from src.platform.common.clock import Clock, SystemClock
from src.platform.common.errors import NotFoundError
from src.platform.common.ids import generate_id
from src.platform.common.repository import InMemoryRepository
from src.platform.storage.models import StorageClass, StoredObject
from src.platform.storage.providers import InMemoryStorageProvider, StorageProvider


class StorageService:
    """Store and catalogue artifacts across storage classes, per tenant."""

    def __init__(
        self,
        *,
        catalogue: InMemoryRepository[StoredObject] | None = None,
        default_provider: StorageProvider | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.catalogue = catalogue or InMemoryRepository("stored_object")
        self._default = default_provider or InMemoryStorageProvider()
        self._clock = clock or SystemClock()
        self._providers: dict[StorageClass, StorageProvider] = {}

    def register_provider(
        self, storage_class: StorageClass, provider: StorageProvider
    ) -> None:
        """Bind a provider to a storage class."""
        self._providers[storage_class] = provider

    def _provider_for(self, storage_class: StorageClass) -> StorageProvider:
        """Return the provider for a class (falls back to the default)."""
        return self._providers.get(storage_class, self._default)

    def put(
        self,
        tenant_id: str,
        organization_id: str,
        key: str,
        data: bytes,
        *,
        storage_class: StorageClass = StorageClass.OBJECT,
        content_type: str = "application/octet-stream",
    ) -> StoredObject:
        """Store bytes and record catalogue metadata; return the record."""
        provider = self._provider_for(storage_class)
        provider.put(tenant_id, key, data)
        now = self._clock.now()
        record = StoredObject(
            id=generate_id("obj"),
            tenant_id=tenant_id,
            organization_id=organization_id,
            key=key,
            storage_class=storage_class,
            content_type=content_type,
            size_bytes=len(data),
            checksum=hashlib.sha256(data).hexdigest(),
            cdn_url=provider.url(tenant_id, key),
            created_at=now,
            updated_at=now,
        )
        return self.catalogue.add(record)

    def get(
        self, tenant_id: str, key: str, *, storage_class: StorageClass = StorageClass.OBJECT
    ) -> bytes:
        """Return stored bytes, raising :class:`NotFoundError` if absent."""
        data = self._provider_for(storage_class).get(tenant_id, key)
        if data is None:
            raise NotFoundError(f"object '{key}' not found")
        return data

    def delete(
        self, tenant_id: str, key: str, *, storage_class: StorageClass = StorageClass.OBJECT
    ) -> None:
        """Delete bytes and de-catalogue the object."""
        self._provider_for(storage_class).delete(tenant_id, key)
        for record in self.catalogue.list(
            tenant_id=tenant_id, where=lambda o: o.key == key
        ):
            self.catalogue.delete(record.id, tenant_id=tenant_id)

    def archive(self, tenant_id: str, key: str) -> StoredObject | None:
        """Move an object's catalogue entry to the ARCHIVE class."""
        matches = self.catalogue.list(tenant_id=tenant_id, where=lambda o: o.key == key)
        if not matches:
            return None
        record = matches[0]
        record.storage_class = StorageClass.ARCHIVE
        record.touch(self._clock.now())
        return self.catalogue.update(record)

    def list_objects(self, tenant_id: str) -> list[StoredObject]:
        """Return the tenant's stored-object catalogue."""
        return self.catalogue.list(tenant_id=tenant_id)

    def usage_bytes(self, tenant_id: str) -> int:
        """Return the total catalogued bytes for a tenant."""
        return sum(o.size_bytes for o in self.catalogue.list(tenant_id=tenant_id))
