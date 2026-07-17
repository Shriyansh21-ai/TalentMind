# TalentMind — API Reference

TalentMind does **not** ship a bound HTTP server. Its "APIs" are:

1. **In-process service classes** — the public surface of the AI platform and the enterprise
   platform, called directly from Python (and from the Streamlit UI).
2. **REST-ready contracts** (`src/platform/api`) — envelopes, pagination, filtering, versioning,
   rate limiting, and an OpenAPI skeleton, designed to sit behind a future REST layer.

This document catalogues those contracts. It does not invent endpoints that do not exist.

---

## 1. REST-ready contracts — `src/platform/api`

| Module | Types / functions | Purpose |
|---|---|---|
| `responses.py` | `ApiResponse[T]`, `ApiError`, `ResponseMeta`, `ok(...)`, `fail(...)` | Standard response envelopes. |
| `errors.py` | `STATUS_BY_CODE`, `http_status_for`, `to_response` | Map `common.errors` → HTTP status. |
| `pagination.py` | `PageRequest`, `Page[T]`, `paginate`, `CursorPage[T]`, `cursor_paginate`, `encode_cursor`, `decode_cursor` | Offset & opaque-cursor pagination. |
| `filtering.py` | `Operator`, `FilterSpec`, `SortSpec`, `apply_filters`, `apply_sorts` | Declarative filtering & sorting. |
| `versioning.py` | `ApiVersion` (only `V1`), `CURRENT_VERSION`, `SUPPORTED_VERSIONS`, `negotiate` | URL-prefix versioning (`/api/v1`). |
| `ratelimit.py` | `RateLimiter` Protocol, `TokenBucketRateLimiter`, `RateLimitResult` | Deterministic token-bucket rate limiting (reused by runtime). |
| `openapi.py` | `build_openapi(title=...)` | OpenAPI 3.1 skeleton dict. |

### Error → HTTP status map (`STATUS_BY_CODE`)

| Error code | HTTP |
|---|---|
| `validation_error` | 422 |
| `not_found` | 404 |
| `conflict` | 409 |
| `tenant_isolation_violation` | 403 |
| `authentication_failed` | 401 |
| `session_invalid` | 401 |
| `permission_denied` | 403 |
| `quota_exceeded` | 429 |
| `feature_disabled` | 403 |
| `license_error` | 402 |
| (else) | 500 |

### Building a response

```python
from src.platform.api.responses import ok, fail
from src.platform.api.errors import to_response

ok({"candidate_id": "CAND_1"})            # ApiResponse envelope
to_response(some_platform_error)          # maps a PlatformError to an ApiError + status
```

---

## 2. Enterprise platform façade — `src/platform/bootstrap`

The single composition root. `build_platform(*, clock=None)` returns a `Platform` exposing lazy
service accessors:

```python
from src.platform.bootstrap import build_platform

p = build_platform()
p.organizations   # OrganizationService
p.tenants         # TenantService
p.auth            # AuthenticationManager
p.access_control  # AccessControlService (RBAC)
p.workspaces      # WorkspaceService
p.config          # ConfigurationService
p.subscriptions   # SubscriptionService
p.notifications   # NotificationService
p.audit           # PlatformAuditService
p.storage         # StorageService
p.extensions      # developer/ExtensionRegistry
p.integrations    # IntegrationPlatform
p.runtime         # RuntimePlatform
p.security        # SecurityPlatform
p.deployment      # DeploymentPlatform

# High-level orchestrated flow:
org, tenant = p.provision_organization("Acme Inc", slug="acme")
```

Key service method groups (selected — see [`SECURITY.md`](SECURITY.md), [`RUNTIME.md`](RUNTIME.md),
[`INTEGRATIONS.md`](INTEGRATIONS.md), [`DEPLOYMENT.md`](DEPLOYMENT.md) for full detail):

| Service | Representative methods |
|---|---|
| `OrganizationService` | `create_organization`, `set_status`, `update_settings`, `add_business_unit` |
| `AuthenticationManager` | `register_user`, `login`, `logout`, `change_password`, `reset_password` |
| `AccessControlService` | `assign`, `revoke`, `authorize`, `is_allowed`, `effective_permissions` |
| `ConfigurationService` | `ensure`, `set_feature`, `is_feature_enabled`, `set_license`, `is_licensed_for` |
| `SubscriptionService` | `subscribe`, `change_plan`, `record_usage`, `allocate_seat` |
| `PlatformAuditService` | `record`, `query`, `recent`, `verify_chain` |

All persistence is in-memory (`InMemoryRepository`), and every tenant-scoped read/write is
isolation-checked (`TenantIsolationError`).

---

## 3. AI platform façade — `src/ai/services/hiring_analyst_service.py`

```python
from src.ai.services.hiring_analyst_service import (
    analyze_candidate, peek_cached_analysis, get_platform_status, recent_telemetry,
)

result = analyze_candidate(insights, interview_plan, jd)   # -> AgentResult
result.ok        # bool
result.data      # typed, score-free schema instance
result.status    # SUCCESS | CACHED | FALLBACK | FAILED
```

Agents are invoked through `AgentRunner.run(agent, payload, config)` and return an `AgentResult`
(see [`AI_PLATFORM.md`](AI_PLATFORM.md)). Each agent's input dataclass and output schema are
documented in [`ENTERPRISE_AGENTS.md`](ENTERPRISE_AGENTS.md).

### Request / response model

- **Request** — each agent defines a typed `*Input` dataclass (e.g. `HiringAnalystInput`).
- **Response** — a Pydantic schema subclassing `BaseAIResponse` (e.g. `HiringAnalysis`), always
  **score-free**, wrapped in an `AgentResult` envelope carrying status, provider/model, cache flag,
  retries, latency, token usage, warnings, and error.

### Authentication

The in-process APIs are not network-exposed and therefore carry no HTTP authentication. When you
put a REST layer in front of the `src/platform/api` contracts, authenticate via the
`AuthenticationManager` (sessions) and authorize via `AccessControlService` / the security
platform's `AuthorizationEngine`, then map failures through `api/errors.py`.
