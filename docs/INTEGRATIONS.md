# TalentMind — Integration Platform

The integration platform (`src/platform/integrations`) is a uniform, swappable **provider model**
for connecting to HRIS / ATS / calendar / communication / document ecosystems, plus an API
gateway, webhook platform, event bus, sync framework, marketplace, and SDK.

> **Important:** everything here is **interfaces and simulated behavior — no real network call is
> ever made.** The provider classes carry real declarative metadata and capability declarations,
> but no live API is implemented. To go live, implement the transport behind the provider seam and
> supply credentials via the credential vault. This is an integration *architecture*, ready to be
> wired, not a set of live connectors.

Built by `build_integration_platform(clock, registry)` into an `IntegrationPlatform` dataclass
(DI keys `intg.*`). Version `__version__ = "6.2.0"`.

```python
from src.platform.bootstrap import build_platform
p = build_platform()
intg = p.integrations
intg.manager.available_providers()      # catalogue
```

---

## Provider model (`integrations/common`)

- `IntegrationProvider` Protocol + `BaseIntegrationProvider` — the provider seam. `describe`,
  `validate_configuration`, and `check_health` (returns a synthetic `UNKNOWN` — "offline reference
  provider, no live probe performed").
- Models: `Integration`, `IntegrationDefinition`, `IntegrationConfiguration`,
  `IntegrationMetadata`, `IntegrationCapabilities`, `IntegrationHealth`, `IntegrationStatus`,
  `ProviderCategory`, `AuthScheme`, `SyncDirection`.
- `IntegrationRegistry` + `build_default_registry`.
- `CredentialVault` (`secrets.py`) — opaque credential references with redaction.

### Provider catalogues

Provider *interfaces* are declared per category (49 provider classes total). Example — HRIS
(`hris/providers.py`, 12 providers): Workday, SAP SuccessFactors, Oracle HCM, ADP, BambooHR,
Rippling, Darwinbox, UKG, HiBob, Personio, Greenhouse-HRIS, Ashby-HRIS. Analogous catalogues exist
for ATS (`ats/`), calendar (`calendar/`), communication (`communication/`), and documents
(`documents/`). Each provider exposes real metadata + capability declarations; `all_providers()`
returns instances.

---

## Control plane — `IntegrationManager` (`manager.py`)

Tenant-scoped, isolation-checked lifecycle management, emitting logs + events:

`available_providers`, `install`, `get`/`list`, `configure`, `connect` (simulated → `HEALTHY`),
`disconnect`, `disable`, `check_health`, `credential_preview`, `require_connected`, `uninstall`.

---

## API gateway (`gateway/`)

An **in-process** request-object gateway (not a bound HTTP server):

- `ApiGateway.handle(request)` runs `_authenticate` → `_authorize` → `_rate_limit` → route.
- `Router` / `ApiRoute` / `RegisteredRoute` / `HttpMethod`.
- `auth.py`: `ApiPrincipal`, `AuthenticationHook` Protocol, `StaticApiKeyAuthHook`, `RateLimitHook`.

## Webhooks (`webhooks/`)

`WebhookService` — `register`, `dispatch`, `retry`, `deliveries`, `dead_letters`, `receive`.
`WebhookSigner` provides **HMAC** signing and `verify`. Models: `WebhookSubscription`,
`WebhookDelivery`, `InboundReceipt`.

## Event bus (`events/`)

`EnterpriseEventBus` — `publish`, `subscribe`, `unsubscribe`, `replay`, `history`, `dead_letters`,
`redeliver_dead_letters`. `MessageBroker` Protocol. This is the bus the **runtime platform**
publishes onto (`runtime.events`).

## Synchronization (`sync/`)

`SynchronizationService` — `schedule`, `run`, `recover`, `resolve`, `jobs`, `health`. Models:
`SyncJob`, `SyncBatch`, `SyncConflict`, `SyncMode`, `ConflictResolution`.

## Marketplace & SDK

`marketplace.py::MarketplaceService` (read-side aggregation);
`observability/metrics.py::ObservabilityRegistry`; `sdk/foundation.py`.

---

## Adding a live connector

1. Subclass `BaseIntegrationProvider` for your system and declare its
   `IntegrationDefinition` / `IntegrationCapabilities`.
2. Implement the real transport in `check_health` / the sync + gateway hooks.
3. Store credentials through the `CredentialVault` (never in code or config files).
4. Register it via the `IntegrationRegistry` so it appears in `available_providers()` and the
   marketplace.

See [`RUNTIME.md`](RUNTIME.md) for the event bus consumer side and
[`SECURITY.md`](SECURITY.md) for credential handling.
