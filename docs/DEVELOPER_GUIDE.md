# TalentMind — Developer Guide

Everything a contributor needs: environment setup, coding standards, the
extension/plugin model, and the contribution workflow. Pairs with
`ARCHITECTURE.md` (structure) and `DISASTER_RECOVERY.md` (operations).

---

## 1. Getting started

```bash
# Clone and create a virtualenv (Python 3.11+ ; 3.13 recommended)
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install runtime + test dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run the app
streamlit run app.py

# Run the tests
pytest -q
```

Set the environment with `TALENTMIND_ENV` (`development` | `testing` |
`staging` | `production` | `air_gapped` | `offline_enterprise` | `cloud` |
`hybrid`). Defaults to `development`.

---

## 2. Coding standards

- **SOLID + Clean Architecture.** Separate `models.py` (pydantic) from
  `service.py`/engines; define interfaces (Protocol/ABC) before implementations.
- **DRY / KISS.** Reuse the shared primitives in `src/platform/common`
  (base models, errors, ids, clock, repository). Do not duplicate logic —
  e.g. the RBAC permission grammar and the secret/encryption seam are reused
  across platforms, never re-implemented.
- **Strong typing.** Full type hints; `from __future__ import annotations` at the
  top of every module. The platform layer type-checks under mypy.
- **Determinism.** Inject the `Clock`; never call `datetime.now()` or sleep in
  library code. No randomness in control flow.
- **Tenant safety.** Persist tenant-owned data as `TenantScopedEntity` and go
  through `InMemoryRepository`, which enforces isolation at the boundary.
- **Docstrings.** Module + public class/function docstrings (Google style),
  matching the density of the surrounding code.
- **Formatting/lint.** `ruff format` + `ruff check` (config in `pyproject.toml`).

---

## 3. Design patterns in use

| Pattern | Where |
|---|---|
| Repository | `common.repository.InMemoryRepository` (all services) |
| Provider | integration providers, cache/secret/metrics/exporter seams |
| Factory | registries, `build_default_*`, health-check/maintenance factories |
| Strategy | retry/backoff, execution strategies, ABAC operators, enforcement |
| Builder | `PerformanceProfileBuilder`, release change grouping |
| Dependency Injection | `Container` + `build_*_platform` composition roots |

---

## 4. Extending the platform

### Add an integration provider (M2)
Subclass `BaseIntegrationProvider`, declare `key`, `metadata`, `capabilities`,
and register it: `registry.register(MyProvider())`. Every caller is unchanged.

### Add a background job (M3)
Register a `JobDefinition` + handler with `JobManager.define(...)`, then
`submit(...)`. Retry/priority/dependencies are handled by the framework.

### Add an authorization policy (M4)
Define role hierarchy/groups via `RoleHierarchy`, or add an `AbacPolicy` via
`AuthorizationEngine.add_policy(...)`. Decisions are explainable and default-deny.

### Add a deployment profile / config profile (M5)
Register a `DeploymentProfile` with `DeploymentManager.register_profile(...)`;
add a config profile in `deployment/configuration.py`.

### Plugin development (M2 developer platform)
Implement the `Plugin` protocol with a `PluginManifest`, register via
`ExtensionRegistry.register(...)`, then `enable(...)`. Plugins receive a scoped
`PlatformSDK` (event bus + hooks). See `src/platform/developer`.

---

## 5. Testing

- Mirror the existing test style: deterministic (`FrozenClock`), offline, no
  network, no heavy model loads in platform tests.
- Every new platform sub-package gets: unit tests, an **architecture test**
  asserting it never imports business logic, and (if it adds a UI) a Streamlit
  `AppTest`.
- Run `pytest -q` before opening a PR; the full suite must stay green.

Repository health can be audited any time:

```python
from src.platform.deployment.health_check import RepositoryHealthCheck
print(RepositoryHealthCheck().report_markdown())
```

---

## 6. Contribution workflow

1. Branch from `main` (`feat/…`, `fix/…`, `docs/…`).
2. Keep changes **additive**; never modify Phase 1–5 business logic or existing
   permissions/tests.
3. Add tests + docstrings; run `ruff` and `pytest -q`.
4. Update the relevant doc (`ARCHITECTURE.md` module registry, this guide, etc.).
5. Open a PR — CI runs lint, type-check, tests, security scan, docs validation
   and a container build (see `.github/workflows/ci.yml`).
6. A green CI + review approval is required to merge.

---

## 7. Release engineering

Releases follow **semantic versioning**. Use the in-app `ReleaseManager` to
build manifests, generate notes, track migrations/deprecations and the
compatibility matrix. Tag `vX.Y.Z` to trigger `.github/workflows/release.yml`,
which re-runs the full suite, validates production readiness, builds the image
and packages artifacts.
