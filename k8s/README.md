# TalentMind — Kubernetes Manifests

Raw, controller-agnostic manifests for deploying TalentMind (Phase 6 /
Milestone 5). They are **additive** and change no application code.

## Apply order

Apply in numeric order (the prefixes encode dependencies):

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

Or all at once (excluding the secret template):

```bash
kubectl apply -f k8s/ --prune=false
```

## Contents

| File | Kind | Purpose |
|---|---|---|
| `00-namespace.yaml` | Namespace | Isolates all resources |
| `01-serviceaccount.yaml` | ServiceAccount | Least-privilege identity (token automount off) |
| `02-configmap.yaml` | ConfigMap | Non-secret runtime configuration |
| `03-secret.template.yaml` | Secret (template) | Placeholder — source from a real secret store |
| `04-persistentvolume.yaml` | PV + PVC | Persistent storage for data/outputs/logs |
| `05-deployment.yaml` | Deployment | 3 replicas, health probes, non-root, rolling update |
| `06-service.yaml` | Service | ClusterIP fronting the pods |
| `07-ingress.yaml` | Ingress | TLS + websocket/sticky sessions for Streamlit |
| `08-hpa.yaml` | HorizontalPodAutoscaler | 3–10 replicas on CPU/memory |
| `09-networkpolicy.yaml` | NetworkPolicy | Default-deny with explicit allows |
| `10-poddisruptionbudget.yaml` | PodDisruptionBudget | Keeps ≥2 pods during drains |

## Security posture

- Runs as a non-root user (uid 10001), drops all Linux capabilities, disallows
  privilege escalation.
- Default-deny NetworkPolicy — egress limited to DNS (TalentMind is offline by
  default); open explicit egress when binding real integrations.
- No secrets are required to boot; the secret template targets a real store.

See `HELM_STRUCTURE.md` for the planned (not-yet-built) Helm chart layout.
