# TalentMind — Enterprise Installation Guide (Module 13)

TalentMind ships as an offline-by-default platform. It runs on a laptop, a
single VM, Docker, or Kubernetes with no external services required to boot.

---

## 1. Requirements

- Python **3.11+** (3.13 recommended)
- ~4 GB RAM (8 GB recommended with the optional ML stack)
- No network required for the platform layer; optional ML models download once

Verify an installation programmatically:

```python
from src.platform.deployment import verify_installation
report = verify_installation()
print("valid:", report.valid, "offline_capable:", report.offline_capable)
print("missing required:", report.missing_required)
```

---

## 2. Local install (source)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501.

---

## 3. Docker

```bash
# Production profile
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Development (live reload)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

The image is a multi-stage build running as a non-root user with a Streamlit
health endpoint (`/_stcore/health`).

---

## 4. Kubernetes

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-serviceaccount.yaml
kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/04-persistentvolume.yaml
kubectl apply -f k8s/05-deployment.yaml
kubectl apply -f k8s/06-service.yaml
kubectl apply -f k8s/07-ingress.yaml
kubectl apply -f k8s/08-hpa.yaml
kubectl apply -f k8s/09-networkpolicy.yaml
kubectl apply -f k8s/10-poddisruptionbudget.yaml
```

See `k8s/README.md` for details and `k8s/HELM_STRUCTURE.md` for the planned Helm
chart layout.

---

## 5. Offline / air-gapped installation

```bash
# On a connected host:
pip download -r requirements.txt -d ./wheels

# Transfer ./wheels to the air-gapped host, then:
pip install --no-index --find-links ./wheels -r requirements.txt
TALENTMIND_ENV=offline_enterprise streamlit run app.py
```

The platform layer makes **no** network calls. Only the optional ML models
(`sentence-transformers`, `torch`) require one-time connectivity to download
weights; pre-stage those on the connected host if needed.

---

## 6. Configuration

Configuration is driven by environment profiles
(`development` · `testing` · `production` · `enterprise` · `cloud` · `offline`).
Export a profile's settings:

```python
from src.platform.deployment.configuration import ConfigurationPlatform
print(ConfigurationPlatform().export("production", fmt="env"))
```

Environment variables use the `TALENTMIND_` prefix (e.g.
`TALENTMIND_ENV`, `TALENTMIND_LOG_LEVEL`, `TALENTMIND_WORKERS`).

---

## 7. Production readiness

Before going live, run the production validator:

```python
from src.platform.deployment import build_deployment_platform
report = build_deployment_platform().validator.validate()
print("ready:", report.ready, "score:", round(report.score, 2))
```

A `ready == True` result with no critical failures indicates the environment is
prepared for production.

---

## 8. Secrets

No secrets are required to boot. For production integrations, source secrets from
a real store (HashiCorp Vault, Azure Key Vault, AWS/GCP Secret Manager) via the
security platform's `SecretManager` provider seam or the k8s External Secrets
Operator — never commit secrets to git (see `k8s/03-secret.template.yaml`).
