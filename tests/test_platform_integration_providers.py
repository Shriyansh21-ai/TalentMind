"""Modules 2-6 tests — HRIS, ATS, calendar, communication and document providers.

Verifies each provider family exposes the required set of swappable provider
interfaces with sensible capability declarations, and exercises the domain
models that ship with the calendar, communication and document families
(timezone conversion, template rendering, document versioning).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.platform.integrations.ats import all_providers as ats_providers
from src.platform.integrations.calendar import (
    Availability,
    InterviewSlot,
    SlotStatus,
    TimeWindow,
    convert_timezone,
)
from src.platform.integrations.calendar import all_providers as cal_providers
from src.platform.integrations.common.models import ProviderCategory
from src.platform.integrations.communication import (
    ChannelType,
    MessageTemplate,
)
from src.platform.integrations.communication import all_providers as comm_providers
from src.platform.integrations.documents import (
    DocumentKind,
    DocumentMetadata,
    StorageAbstraction,
)
from src.platform.integrations.documents import all_providers as doc_providers
from src.platform.integrations.hris import all_providers as hris_providers


# -- provider coverage ------------------------------------------------------


def test_hris_family_covers_required_vendors():
    keys = {p.key for p in hris_providers()}
    assert {
        "workday", "sap_successfactors", "oracle_hcm", "adp", "bamboohr",
        "rippling", "darwinbox", "ukg", "hibob", "personio",
        "greenhouse_hris", "ashby_hris",
    } <= keys
    assert all(p.category == ProviderCategory.HRIS for p in hris_providers())


def test_ats_family_covers_required_vendors():
    keys = {p.key for p in ats_providers()}
    assert {
        "greenhouse", "lever", "smartrecruiters", "ashby", "workable",
        "jazzhr", "icims", "jobvite", "bullhorn", "teamtailor",
    } <= keys
    assert all(p.category == ProviderCategory.ATS for p in ats_providers())


def test_calendar_and_communication_and_document_families():
    assert {p.key for p in cal_providers()} == {
        "google_calendar", "microsoft_outlook", "exchange", "apple_calendar",
    }
    assert {p.key for p in comm_providers()} == {
        "email", "slack", "microsoft_teams", "discord", "sms",
        "whatsapp", "webhook_notifications",
    }
    assert {p.key for p in doc_providers()} == {
        "google_drive", "onedrive", "sharepoint", "dropbox", "box",
        "amazon_s3", "azure_blob",
    }


def test_provider_describe_roundtrips_capabilities():
    workday = next(p for p in hris_providers() if p.key == "workday")
    definition = workday.describe()
    assert definition.key == "workday"
    assert definition.capabilities.supports_incremental_sync
    assert definition.category == ProviderCategory.HRIS


# -- calendar models --------------------------------------------------------


def test_timezone_conversion_shifts_offset():
    utc_noon = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    ist = convert_timezone(utc_noon, 330)  # +05:30
    assert ist.hour == 17 and ist.minute == 30


def test_availability_and_interview_slot():
    window = TimeWindow(
        start=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 17, 0, tzinfo=timezone.utc),
    )
    availability = Availability(participant_id="u1", free_windows=[window])
    slot_window = TimeWindow(
        start=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
    )
    assert availability.is_free_at(slot_window)
    assert slot_window.duration_minutes == 60

    slot = InterviewSlot(
        id="slot_1", tenant_id="t1", organization_id="t1", window=slot_window
    )
    assert slot.status == SlotStatus.OPEN


# -- communication models ---------------------------------------------------


def test_template_renders_safely():
    template = MessageTemplate(
        id="tpl_1",
        tenant_id="t1",
        organization_id="t1",
        key="interview_invite",
        subject="Interview with $company",
        body="Hi $name, your $role interview is confirmed.",
        channel_type=ChannelType.EMAIL,
    )
    subject, body = template.render({"company": "Acme", "name": "Sam", "role": "SWE"})
    assert subject == "Interview with Acme"
    assert "Hi Sam" in body and "SWE interview" in body


def test_template_leaves_unknown_placeholders_intact():
    template = MessageTemplate(
        id="tpl_2", tenant_id="t1", organization_id="t1", key="k", body="Hello $missing"
    )
    _subject, body = template.render({})
    assert body == "Hello $missing"


# -- document models --------------------------------------------------------


def test_document_versioning_advances():
    doc = DocumentMetadata(
        id="doc_1",
        tenant_id="t1",
        organization_id="t1",
        name="offer.pdf",
        kind=DocumentKind.OFFER_LETTER,
    )
    v1 = doc.add_version(checksum="aaa", size_bytes=10)
    v2 = doc.add_version(checksum="bbb", size_bytes=20)
    assert (v1.version, v2.version) == (1, 2)
    assert doc.current_version == 2
    assert len(doc.versions) == 2


def test_storage_abstraction_namespaces_by_tenant():
    storage = StorageAbstraction(provider_key="amazon_s3", root="/docs", bucket="b")
    key = storage.resolve_key("tenant_x", "resumes/cv.pdf")
    assert key == "/docs/t/tenant_x/resumes/cv.pdf"
