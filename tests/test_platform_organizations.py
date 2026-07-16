"""Tests for Module 1 — Enterprise Organizations."""

from __future__ import annotations

import faiss  # noqa: F401

import pytest

from src.platform.common import FrozenClock, TenantIsolationError
from src.platform.common.errors import ConflictError, PlatformValidationError
from src.platform.organizations import OrganizationService, OrganizationStatus
from src.platform.organizations.models import Location


def _service() -> OrganizationService:
    return OrganizationService(clock=FrozenClock())


def test_create_organization_defaults():
    svc = _service()
    org = svc.create_organization("Acme Inc")
    assert org.slug == "acme-inc"
    assert org.status == OrganizationStatus.TRIAL
    assert org.is_operational()
    assert org.limits.max_users == 25


def test_slug_uniqueness_enforced():
    svc = _service()
    svc.create_organization("Acme", slug="acme")
    with pytest.raises(ConflictError):
        svc.create_organization("Acme Two", slug="acme")


def test_blank_legal_name_rejected():
    with pytest.raises(PlatformValidationError):
        _service().create_organization("   ")


def test_hierarchy_business_unit_department_office():
    svc = _service()
    org = svc.create_organization("Acme")
    bu = svc.add_business_unit(org.id, "EMEA", code="EMEA")
    dept = svc.add_department(org.id, "TA", business_unit_id=bu.id)
    office = svc.add_office(org.id, "HQ", location=Location(city="Berlin"), is_headquarters=True)
    assert dept.business_unit_id == bu.id
    assert office.is_headquarters and office.location.city == "Berlin"
    assert len(svc.business_units(org.id)) == 1
    assert len(svc.departments(org.id)) == 1
    assert len(svc.offices(org.id)) == 1


def test_children_are_tenant_scoped_to_org():
    svc = _service()
    a = svc.create_organization("A", slug="a")
    b = svc.create_organization("B", slug="b")
    svc.add_business_unit(a.id, "Unit A")
    # A department in B cannot reference A's business unit (cross-tenant).
    unit_a = svc.business_units(a.id)[0]
    with pytest.raises(TenantIsolationError):
        svc.add_department(b.id, "Dept", business_unit_id=unit_a.id)


def test_status_and_settings_updates():
    svc = _service()
    org = svc.create_organization("Acme")
    svc.set_status(org.id, OrganizationStatus.SUSPENDED)
    assert not svc.require_organization(org.id).is_operational()
    settings = org.settings.model_copy(update={"default_language": "de"})
    svc.update_settings(org.id, settings)
    assert svc.get_organization(org.id).settings.default_language == "de"


def test_features_resolution():
    svc = _service()
    org = svc.create_organization("Acme")
    assert org.features.enabled("api_access") is True
    assert org.features.enabled("unknown_feature") is False
