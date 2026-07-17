# TalentMind — Deployment

TalentMind ships as an **offline-by-default** Streamlit application. It runs on a laptop, a single
VM, Docker, Docker Compose, or Kubernetes. This document covers the deployment topologies and the
in-app deployment platform that plans and validates them. For installation prerequisites see
[`INSTALL.md`](INSTALL.md); for day-2 operations see [`OPERATIONS.md`](OPERATIONS.md); for recovery
see [`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md).

---

## 1. Local

```bash
pip install -r requirements.txt
streamlit run app.py            # http://localhost:8501
```

## 2. Docker

The `Dockerfile` is a multi-stage build (builder venv → slim runtime), runs as a **non-root** user
(`uid 10001`), and defines a `HEALTHCHECK` against Streamlit's `/_stcore/health`.

```bash
docker build -t talentmind:1.0.0 .
docker run -p 8501:8501 talentmind:1.0.0
```

Image labels declare `org.opencontainers.image.*` metadata (title, version `1.0.0`, MIT license).
Writable runtime dirs (`/app/data`, `/app/outputs`, `/app/logs`) are created and owned by the
non-root user.

## 3. Docker Compose

Three compose files are provided:

| File | Use |
|---|---|
| `docker-compose.yml` | Base service definition. |
| `docker-compose.dev.yml` | Development overrides. |
| `docker-compose.prod.yml` | Production overrides. |

```bash
docker compose up                                  # base
docker compose -f docker-compose.dev.yml up        # dev
docker compose -f docker-compose.prod.yml up       # prod
```

## 4. Kubernetes

Raw, controller-agnostic manifests live in `k8s/`, prefixed to encode apply order. Apply in
numeric order (see `k8s/README.md`):

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-serviceaccount.yaml
kubectl apply -f k8s/02-configmap.yaml
# 03-secret.template.yaml — copy, fill, and apply out of band (never commit real values)
kubectl apply -f k8s/04-persistentvolume.yaml
kubectl apply -f k8s/05-deployment.yaml
kubectl apply -f k8s/06-service.yaml
kubectl apply -f k8s/07-ingress.yaml
kubectl apply -f k8s/08-hpa.yaml
kubectl apply -f k8s/09-networkpolicy.yaml
kubectl apply -f k8s/10-poddisruptionbudget.yaml
```

The manifests include a namespace, service account, config map, secret template, persistent
volume, deployment, service, ingress, horizontal pod autoscaler, network policy, and pod
disruption budget. A prospective Helm chart layout is sketched in `k8s/HELM_STRUCTURE.md` (not yet
built).

---

## 5. In-app deployment platform — `src/platform/deployment`

The deployment platform **plans, validates, versions, and measures** deployments. The actual
Docker/K8s/CI artifacts live at the repo root; this layer models the operations around them.
Built by `build_deployment_platform(clock)`; version `1.0.0` (it ships TalentMind as v1.0.0
Enterprise Edition).

| Component | Module | Responsibility |
|---|---|---|
| `DeploymentManager` | `manager.py` | `register_profile`, `validate`, `create_plan`, `create_rollback_plan`, `deploy`, `rollback`, `health`. |
| `EnvironmentDetector` | `environment.py` | `detect`, `is_production`, `is_offline`, `describe`. |
| `ConfigurationPlatform` | `configuration.py` | Env config profiles: `profiles`, `load`, `validate`, `export`, `template`, `document`. |
| `BackupManager` | `backup.py` | `backup`, `validate_restore`, `restore`, `recovery_plan`, `recovery_report`. `LocalBackupProvider` (real). |
| `ReleaseManager` | `release.py` | `SemanticVersion` parse/bump, release notes, compatibility matrix, migrations, deprecations. |
| `ProductionValidator` | `validation.py` | `validate(platform)` → `ProductionReadinessReport` (score/ready; checks config, environment, dependencies, modules, platform, deployment readiness). |
| `BenchmarkRunner` | `benchmark.py` | Real timing benchmarks; `run`, `results`, `system_snapshot`, `report`. |
| packaging | `packaging.py` | `package_info`, `verify_installation`, `offline_install_notes`. |

### Production-readiness gate (used by the release workflow)

```python
from src.platform.deployment import build_deployment_platform

report = build_deployment_platform().validator.validate()
assert report.ready, "not production ready"
print(f"score={report.score:.2f}")
```

`verify_installation()` (packaging) returns an `InstallationReport` with `valid`,
`offline_capable`, and `missing_required` — useful as a smoke test after install.

---

## 6. CI / Release pipelines

`.github/workflows/ci.yml` (on push/PR to `main`): **lint + format** (ruff), **type-check** (mypy,
scoped to `src/platform`), **tests** (full suite + architecture guards), **security scan** (bandit
+ pip-audit), **documentation validation** (required docs present), and a **container build** (no
push, no credentials).

`.github/workflows/release.yml` (on a `vX.Y.Z` tag): verify (full regression + production-readiness
validation) → build & package the image, generate release notes via `ReleaseManager`, and upload
artifacts. Registry publishing is intentionally left opt-in — add a registry login + push in your
fork.
