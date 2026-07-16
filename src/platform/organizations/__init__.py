"""Module 1 — Enterprise Organizations.

Models the full organizational hierarchy that every future resource hangs from:

    Organization
      └── Business Unit
            └── Department
      └── Office (a physical Location)
      └── Workspace (logical container — see :mod:`src.platform.workspaces`)

plus the organization's Settings, Branding, Metadata, Limits and Features.

The :class:`~src.platform.organizations.service.OrganizationService` is the
public entry point; models and the repository back it.
"""

from __future__ import annotations

from src.platform.organizations.models import (
    BusinessUnit,
    Department,
    Location,
    Office,
    Organization,
    OrganizationBranding,
    OrganizationFeatures,
    OrganizationLimits,
    OrganizationSettings,
    OrganizationStatus,
)
from src.platform.organizations.repository import OrganizationRepository
from src.platform.organizations.service import OrganizationService

__all__ = [
    "Organization",
    "OrganizationStatus",
    "OrganizationSettings",
    "OrganizationBranding",
    "OrganizationLimits",
    "OrganizationFeatures",
    "BusinessUnit",
    "Department",
    "Office",
    "Location",
    "OrganizationRepository",
    "OrganizationService",
]
