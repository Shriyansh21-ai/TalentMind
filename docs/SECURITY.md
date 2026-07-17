# TalentMind — Security & Governance

This document describes the security controls implemented in `src/platform/`. Everything is
**offline, deterministic, and additive**: it uses only the standard library plus Pydantic, makes
no network calls, and connects to no real IdP or cloud service. Cloud/external provider classes
are explicit stubs that raise a "not ready" error until you supply a transport.

There are two authentication/authorization stacks and two audit trails, by design:

| Concern | Foundation (Module 1–4) | Enterprise (Milestone 4) |
|---|---|---|
| Auth | `platform/auth` (local login, sessions) | `platform/security/identity` (identity lifecycle, provider registry) |
| Authz | `platform/rbac` (RBAC) | `platform/security/authorization` (RBAC + ABAC) |
| Audit | `platform/audit` (hash-chained) | `platform/security/audit` (hash-chained + retention) |

---

## 1. Authentication — `platform/auth`

`AuthenticationManager` (`auth/manager.py`) is the façade: `register_user`, `login`, `logout`,
`register_device`, `change_password`, `reset_password`.

- **Password hashing** (`auth/passwords.py`) — `PasswordHasher` uses **PBKDF2-HMAC-SHA256 with
  240,000 iterations** and a random 16-byte salt; verification is constant-time
  (`hmac.compare_digest`). No plaintext is ever stored.
- **Password policy** — `PasswordPolicy`: min length 12, requires upper/lower/digit/symbol, max
  age 180 days, blocks reuse of the last 5 passwords.
- **Sessions** (`auth/sessions.py`) — `SessionManager` issues sessions with single-use **rotating
  refresh tokens** (replay-resistant). Tokens are returned in plaintext once and stored only as
  SHA-256 hashes. TTLs: 8h default, 30d remember-me, 30d refresh.
- **Identity seam** (`auth/identity.py`) — `IdentityProvider` Protocol (SSO-ready) +
  `LocalIdentityProvider` with uniform error messages and timing-uniform verification (no user
  enumeration).
- **Recovery** (`auth/recovery.py`) — `EmailVerificationService`, `AccountRecoveryService`.

## 2. Authorization — `platform/rbac`

- **Roles** (`rbac/roles.py`) — 12 built-in roles: `PLATFORM_ADMIN`, `ORGANIZATION_ADMIN`,
  `HR_DIRECTOR`, `RECRUITER`, `HIRING_MANAGER`, `INTERVIEWER`, `FINANCE`, `COMPLIANCE`, `AUDITOR`,
  `EXECUTIVE`, `VIEWER`, `GUEST`. `DEFAULT_ROLE_PERMISSIONS` is a least-privilege matrix
  (`PLATFORM_ADMIN = *:*`).
- **Permissions** (`rbac/permissions.py`) — `Resource` (19 values incl. candidate, pipeline,
  compensation, ai_agent, audit), `Action` (create/read/update/delete/manage/export/approve/
  execute), `permission(resource, action)`, `matches(granted, required)` (wildcard-aware).
- **Policy** (`rbac/policy.py`) — `PolicyEngine` is **default-deny (Zero-Trust)**. Scopes:
  platform / organization / workspace / resource. Platform/organization grants cover the tenant;
  workspace and resource grants must match ids.
- **Service** (`rbac/service.py`) — `AccessControlService`: `define_custom_role`, `assign`
  (rejects platform-only roles below platform scope), `revoke`, `authorize` (raises
  `PermissionDeniedError`), `effective_permissions`.

## 3. Enterprise security platform — `platform/security`

Built by `build_security_platform(clock)` into a `SecurityPlatform` dataclass (its own DI
container, keys `sec.*`). Modules:

| Module | Service | Highlights |
|---|---|---|
| identity | `IdentityManager` | lifecycle + provider registry. **Future providers** (`AzureAdProvider`, `OktaProvider`, `Auth0Provider`, `GoogleWorkspaceProvider`, `LdapProvider`, `SamlProvider`, `OidcProvider`) are stubs that raise "not ready". |
| authorization | `AuthorizationEngine` | combined **RBAC + ABAC**, deny-overrides, default-deny, explainable `DecisionReport`. |
| audit | `EnterpriseAuditService` | hash-chained; `record`, `search`, `verify_chain`, retention policies. |
| secrets | `SecretManager` | `store`/`rotate`/`reveal` (logged), redaction. `LocalSecretProvider` real; Vault/Azure/AWS/GCP providers stub "not ready". |
| observability | `ObservabilityService` | logs/metrics/traces; OTel/Prometheus/Grafana exporters are no-ops. |
| monitoring | `MonitoringService` | rules, notification hooks, alerts. |
| governance | `GovernanceService` | policy registration, exceptions, enforcement. |
| compliance | `ComplianceService` | control catalogues for **GDPR, SOC 2, ISO 27001, HIPAA, PCI-DSS, AI-governance**; evidence, assessment, gap analysis. |
| threat | `ThreatDetectionService` | access-violation / escalation / config-drift detection. |
| configuration | `ConfigurationGovernanceService` | versioned config with approval workflow, rollback. |
| incidents | `IncidentService` | open/assign/escalate/resolve/close, root cause. |
| analytics | `OperationalAnalyticsService` | security/audit/policy/incident/monitoring metrics + executive dashboard. |

## 4. Audit trails

Both `platform/audit` (Module 9) and `platform/security/audit` (Milestone 4) are **tamper-evident
hash chains**: each entry's digest incorporates the previous entry's, and `verify_chain` detects
any tampering. `platform/audit` chains per tenant. `bootstrap.provision_organization` writes an
audit event as part of provisioning.

## 5. Tenant isolation

Isolation is enforced at the data boundary. `common/repository.py::InMemoryRepository` refuses any
cross-tenant read/write and raises `TenantIsolationError`. `tenancy/isolation.py::
TenantIsolationGuard` provides `assert_entity_in_scope`, `assert_tenant_matches`, and namespaced
keys. Tenant context is ambient (contextvar-backed) and entered at the edge by `TenantMiddleware`.

## 6. Cryptography summary

| Use | Primitive |
|---|---|
| Password storage | PBKDF2-HMAC-SHA256, 240k iterations, 16-byte salt |
| Session / refresh tokens | SHA-256 hash at rest, plaintext returned once |
| Webhook signing | HMAC (`integrations/webhooks::WebhookSigner`) |
| Audit chaining | SHA-256 hash chain |

## 7. Reporting a vulnerability

This is a demonstration/open-source platform. If you deploy it, add a `SECURITY.md` policy at the
repository root with your disclosure contact and supported-versions table before going live.
Never commit real secrets — `k8s/03-secret.template.yaml` is a template to be filled out of band.
