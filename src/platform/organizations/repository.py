"""Persistence for the organization aggregate (Module 1).

:class:`OrganizationRepository` bundles the in-memory collections for the
organization and its hierarchy (business units, departments, offices). Bundling
the aggregate's collections in one repository keeps the service dependency
surface small while still delegating all storage mechanics to the reusable
:class:`~src.platform.common.repository.InMemoryRepository`.
"""

from __future__ import annotations

from src.platform.common.repository import InMemoryRepository
from src.platform.organizations.models import (
    BusinessUnit,
    Department,
    Office,
    Organization,
)


class OrganizationRepository:
    """Aggregate repository for organizations and their sub-structures."""

    def __init__(self) -> None:
        self.organizations: InMemoryRepository[Organization] = InMemoryRepository("organization")
        self.business_units: InMemoryRepository[BusinessUnit] = InMemoryRepository("business_unit")
        self.departments: InMemoryRepository[Department] = InMemoryRepository("department")
        self.offices: InMemoryRepository[Office] = InMemoryRepository("office")

    def by_slug(self, slug: str) -> Organization | None:
        """Return the organization with ``slug`` (or ``None``)."""
        matches = self.organizations.list(where=lambda o: o.slug == slug)
        return matches[0] if matches else None
