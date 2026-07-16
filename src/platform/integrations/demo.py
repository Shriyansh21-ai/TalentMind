"""Offline demo fixture for the Integration Marketplace workspace (Module 11).

Builds a fully-wired :class:`IntegrationPlatform` pre-seeded with a handful of
installed integrations across a couple of demo tenants — connected, configured,
with simulated sync jobs, webhook subscriptions and telemetry — so the
marketplace dashboard and its AppTest render instantly with no dataset, provider
or network. A :class:`FrozenClock` drives time, so everything is deterministic.
"""

from __future__ import annotations

from src.platform.common.clock import FrozenClock
from src.platform.integrations.bootstrap import (
    IntegrationPlatform,
    build_integration_platform,
)
from src.platform.integrations.sync.models import SyncBatch, SyncConflict, SyncMode
from src.platform.integrations.webhooks.models import WebhookDirection

# (tenant_id, org_id, [(provider_key, credential, sync, webhook)])
_SEED = [
    (
        "org_acme",
        "org_acme",
        [
            ("workday", "wd-token-ACME01", True, True),
            ("greenhouse", "gh-key-ACME02", True, True),
            ("slack", "xoxb-ACME03", False, False),
            ("google_calendar", "gcal-ACME04", False, True),
        ],
    ),
    (
        "org_globex",
        "org_globex",
        [
            ("bamboohr", "bh-key-GLOBEX1", True, False),
            ("lever", "lv-key-GLOBEX2", True, True),
            ("google_drive", "gd-token-GLOBEX3", False, False),
        ],
    ),
]


def _seed_sync_runner(job):
    """Deterministic sync runner that reports a little work + one conflict."""
    return SyncBatch(
        records_processed=42,
        records_failed=0,
        conflicts=[
            SyncConflict(entity_id="emp_1001", field="title", source_value="Staff Engineer", target_value="Senior Engineer")
        ],
        next_cursor="cursor-2026-01-01",
    )


def build_integration_demo() -> IntegrationPlatform:
    """Return an :class:`IntegrationPlatform` seeded with demo integrations."""
    platform = build_integration_platform(clock=FrozenClock())
    platform.sync._runner = _seed_sync_runner  # deterministic offline runner

    for tenant_id, org_id, specs in _SEED:
        for key, credential, sync_enabled, webhook_enabled in specs:
            integration = platform.manager.install(
                tenant_id,
                org_id,
                key,
                credential=credential,
                sync_enabled=sync_enabled,
                webhook_enabled=webhook_enabled,
            )
            platform.manager.connect(tenant_id, integration.id)

            if sync_enabled:
                job = platform.sync.schedule(
                    tenant_id, org_id, integration.id, mode=SyncMode.INCREMENTAL
                )
                platform.sync.run(tenant_id, job.id)

            if webhook_enabled:
                platform.webhooks.register(
                    tenant_id,
                    org_id,
                    f"https://hooks.{tenant_id}.example.com/{key}",
                    secret=f"whsec-{key}",
                    direction=WebhookDirection.OUTGOING,
                    event_filters=["integration.*"],
                )
                platform.webhooks.dispatch(
                    tenant_id,
                    "integration.connected",
                    {"integration_id": integration.id, "provider": key},
                )

    return platform
