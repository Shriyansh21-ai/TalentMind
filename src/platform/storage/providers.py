"""Storage providers (Module 11) — interfaces + offline reference.

Defines the :class:`StorageProvider` and :class:`VectorStore` seams every real
backend (S3, GCS, Azure Blob, a vector DB) must satisfy, plus in-memory
reference implementations for offline use and tests. Every operation is
tenant-namespaced so one tenant's bytes are never reachable from another's key.
No cloud integration is implemented.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.platform.tenancy.isolation import TenantIsolationGuard


@runtime_checkable
class StorageProvider(Protocol):
    """A byte-oriented, tenant-namespaced storage backend."""

    name: str

    def put(self, tenant_id: str, key: str, data: bytes) -> None: ...
    def get(self, tenant_id: str, key: str) -> bytes | None: ...
    def delete(self, tenant_id: str, key: str) -> None: ...
    def exists(self, tenant_id: str, key: str) -> bool: ...
    def url(self, tenant_id: str, key: str) -> str: ...


class InMemoryStorageProvider:
    """A dict-backed, tenant-namespaced storage provider for offline use."""

    def __init__(self, name: str = "memory", *, cdn_base: str = "cdn://") -> None:
        self.name = name
        self._cdn_base = cdn_base
        self._blobs: dict[str, bytes] = {}

    def put(self, tenant_id: str, key: str, data: bytes) -> None:
        """Store ``data`` under the tenant-namespaced key."""
        self._blobs[TenantIsolationGuard.namespaced_key(tenant_id, key)] = bytes(data)

    def get(self, tenant_id: str, key: str) -> bytes | None:
        """Return the tenant's bytes for ``key`` (or ``None``)."""
        return self._blobs.get(TenantIsolationGuard.namespaced_key(tenant_id, key))

    def delete(self, tenant_id: str, key: str) -> None:
        """Delete the tenant's ``key`` (no-op if absent)."""
        self._blobs.pop(TenantIsolationGuard.namespaced_key(tenant_id, key), None)

    def exists(self, tenant_id: str, key: str) -> bool:
        """Return whether the tenant has an object at ``key``."""
        return TenantIsolationGuard.namespaced_key(tenant_id, key) in self._blobs

    def url(self, tenant_id: str, key: str) -> str:
        """Return a CDN-style URL for the object."""
        return f"{self._cdn_base}{tenant_id}/{key}"


@runtime_checkable
class VectorStore(Protocol):
    """A tenant-namespaced vector index seam."""

    def upsert(
        self, tenant_id: str, vector_id: str, vector: list[float], metadata: dict
    ) -> None: ...
    def query(
        self, tenant_id: str, vector: list[float], *, top_k: int = 5
    ) -> list[tuple[str, float]]: ...


class InMemoryVectorStore:
    """A naive cosine-similarity vector store for offline use and tests."""

    def __init__(self) -> None:
        # namespaced_id -> (vector, metadata)
        self._vectors: dict[str, tuple[list[float], dict]] = {}

    def upsert(
        self, tenant_id: str, vector_id: str, vector: list[float], metadata: dict
    ) -> None:
        """Insert or replace a vector for a tenant."""
        key = TenantIsolationGuard.namespaced_key(tenant_id, vector_id)
        self._vectors[key] = (list(vector), dict(metadata))

    def query(
        self, tenant_id: str, vector: list[float], *, top_k: int = 5
    ) -> list[tuple[str, float]]:
        """Return the top-k most similar vector ids for a tenant."""
        prefix = TenantIsolationGuard.namespaced_key(tenant_id, "")
        scored: list[tuple[str, float]] = []
        for key, (stored, _meta) in self._vectors.items():
            if not key.startswith(prefix):
                continue
            scored.append((key[len(prefix):], _cosine(vector, stored)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    """Return the cosine similarity of two equal-length vectors (0 on mismatch)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
