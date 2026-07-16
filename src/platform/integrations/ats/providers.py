"""ATS provider interfaces (Module 3).

Provider *interfaces* for the major Applicant Tracking Systems. Like the HRIS
family, each is a declarative
:class:`~src.platform.integrations.common.provider.BaseIntegrationProvider` with
real metadata and capability declarations — **no API is implemented**.

ATS integrations are typically bidirectional (jobs and candidates flow both
ways: TalentMind ingests requisitions/applications and can push shortlists and
feedback back), so most declare bidirectional, webhook-capable capabilities.
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

_ATS_ENTITIES = ["job", "candidate", "application", "stage", "interview", "offer"]


def _ats_capabilities(
    *, webhooks: bool = True, write: bool = True
) -> IntegrationCapabilities:
    """Return a standard ATS capability profile (bidirectional)."""
    return IntegrationCapabilities(
        supports_read=True,
        supports_write=write,
        supports_full_sync=True,
        supports_incremental_sync=True,
        supports_webhooks=webhooks,
        supports_realtime=False,
        supports_bulk=True,
        direction=SyncDirection.BIDIRECTIONAL,
        entities=list(_ATS_ENTITIES),
        scopes=["jobs:read", "candidates:read", "candidates:write", "applications:read"],
    )


class _AtsProvider(BaseIntegrationProvider):
    """Base for ATS providers."""

    capabilities = _ats_capabilities()


class GreenhouseProvider(_AtsProvider):
    key = "greenhouse"
    metadata = IntegrationMetadata(
        display_name="Greenhouse",
        vendor="Greenhouse Software, Inc.",
        category=ProviderCategory.ATS,
        description="Greenhouse Recruiting — jobs, candidates, scorecards and offers.",
        website="https://www.greenhouse.io",
        docs_url="https://developers.greenhouse.io",
        logo_emoji="🌱",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.OAUTH2],
        tags=["ats", "recruiting", "popular"],
    )


class LeverProvider(_AtsProvider):
    key = "lever"
    metadata = IntegrationMetadata(
        display_name="Lever",
        vendor="Lever, Inc.",
        category=ProviderCategory.ATS,
        description="Lever CRM + ATS with candidate nurturing.",
        website="https://www.lever.co",
        logo_emoji="🎚️",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.API_KEY],
        tags=["ats", "crm"],
    )


class SmartRecruitersProvider(_AtsProvider):
    key = "smartrecruiters"
    metadata = IntegrationMetadata(
        display_name="SmartRecruiters",
        vendor="SmartRecruiters, Inc.",
        category=ProviderCategory.ATS,
        description="SmartRecruiters enterprise talent acquisition suite.",
        website="https://www.smartrecruiters.com",
        logo_emoji="🧠",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.API_KEY],
        tags=["ats", "enterprise"],
    )


class AshbyProvider(_AtsProvider):
    key = "ashby"
    metadata = IntegrationMetadata(
        display_name="Ashby",
        vendor="Ashby, Inc.",
        category=ProviderCategory.ATS,
        description="Ashby all-in-one recruiting and analytics platform.",
        website="https://www.ashbyhq.com",
        logo_emoji="🔷",
        auth_schemes=[AuthScheme.API_KEY],
        tags=["ats", "modern", "analytics"],
    )


class WorkableProvider(_AtsProvider):
    key = "workable"
    metadata = IntegrationMetadata(
        display_name="Workable",
        vendor="Workable Software Limited",
        category=ProviderCategory.ATS,
        description="Workable hiring platform for SMBs.",
        website="https://www.workable.com",
        logo_emoji="💼",
        auth_schemes=[AuthScheme.API_KEY, AuthScheme.OAUTH2],
        tags=["ats", "smb"],
    )


class JazzHrProvider(_AtsProvider):
    key = "jazzhr"
    metadata = IntegrationMetadata(
        display_name="JazzHR",
        vendor="JazzHR (Employ Inc.)",
        category=ProviderCategory.ATS,
        description="JazzHR recruiting software for small businesses.",
        website="https://www.jazzhr.com",
        logo_emoji="🎷",
        auth_schemes=[AuthScheme.API_KEY],
        tags=["ats", "smb"],
    )
    capabilities = _ats_capabilities(webhooks=False)


class IcimsProvider(_AtsProvider):
    key = "icims"
    metadata = IntegrationMetadata(
        display_name="iCIMS",
        vendor="iCIMS, Inc.",
        category=ProviderCategory.ATS,
        description="iCIMS Talent Cloud enterprise recruiting platform.",
        website="https://www.icims.com",
        logo_emoji="☁️",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.BASIC],
        tags=["ats", "enterprise", "fortune500"],
    )


class JobviteProvider(_AtsProvider):
    key = "jobvite"
    metadata = IntegrationMetadata(
        display_name="Jobvite",
        vendor="Jobvite (Employ Inc.)",
        category=ProviderCategory.ATS,
        description="Jobvite recruiting and talent acquisition suite.",
        website="https://www.jobvite.com",
        logo_emoji="📣",
        auth_schemes=[AuthScheme.OAUTH2, AuthScheme.API_KEY],
        tags=["ats", "enterprise"],
    )


class BullhornProvider(_AtsProvider):
    key = "bullhorn"
    metadata = IntegrationMetadata(
        display_name="Bullhorn",
        vendor="Bullhorn, Inc.",
        category=ProviderCategory.ATS,
        description="Bullhorn ATS + CRM for staffing and recruiting agencies.",
        website="https://www.bullhorn.com",
        logo_emoji="📯",
        auth_schemes=[AuthScheme.OAUTH2],
        tags=["ats", "staffing", "agency"],
    )


class TeamtailorProvider(_AtsProvider):
    key = "teamtailor"
    metadata = IntegrationMetadata(
        display_name="Teamtailor",
        vendor="Teamtailor AB",
        category=ProviderCategory.ATS,
        description="Teamtailor employer-branding-first ATS.",
        website="https://www.teamtailor.com",
        logo_emoji="🧵",
        auth_schemes=[AuthScheme.API_KEY],
        tags=["ats", "employer-brand"],
    )


def all_providers() -> list[BaseIntegrationProvider]:
    """Return one instance of every built-in ATS provider interface."""
    return [
        GreenhouseProvider(),
        LeverProvider(),
        SmartRecruitersProvider(),
        AshbyProvider(),
        WorkableProvider(),
        JazzHrProvider(),
        IcimsProvider(),
        JobviteProvider(),
        BullhornProvider(),
        TeamtailorProvider(),
    ]
