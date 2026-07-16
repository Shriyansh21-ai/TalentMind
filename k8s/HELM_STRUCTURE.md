# TalentMind — Future Helm Chart Structure (architecture only)

Per Milestone 5, we **prepare the architecture** for a Helm chart but do **not**
build one. The raw manifests in this directory map 1:1 onto the templates below;
converting them is mechanical (parameterise values, wrap in `{{ }}`).

```
charts/talentmind/
├── Chart.yaml                 # name, version (chart), appVersion (1.0.0)
├── values.yaml                # default values (see mapping below)
├── values-dev.yaml            # development overrides
├── values-prod.yaml           # production overrides
├── values-offline.yaml        # air-gapped / offline-enterprise overrides
├── templates/
│   ├── _helpers.tpl           # name/label helpers
│   ├── serviceaccount.yaml    # ← 01-serviceaccount.yaml
│   ├── configmap.yaml         # ← 02-configmap.yaml
│   ├── secret.yaml            # ← 03-secret.template.yaml (optional / externalSecrets)
│   ├── pvc.yaml               # ← 04-persistentvolume.yaml (PVC; PV via storageClass)
│   ├── deployment.yaml        # ← 05-deployment.yaml
│   ├── service.yaml           # ← 06-service.yaml
│   ├── ingress.yaml           # ← 07-ingress.yaml
│   ├── hpa.yaml               # ← 08-hpa.yaml
│   ├── networkpolicy.yaml     # ← 09-networkpolicy.yaml
│   ├── pdb.yaml               # ← 10-poddisruptionbudget.yaml
│   └── NOTES.txt              # post-install instructions
└── templates/tests/
    └── test-connection.yaml   # helm test hook hitting /_stcore/health
```

## values.yaml → manifest mapping

| values key | Backs |
|---|---|
| `image.repository`, `image.tag` | Deployment container image |
| `replicaCount` | Deployment replicas |
| `resources` | Deployment requests/limits |
| `autoscaling.{enabled,minReplicas,maxReplicas,targetCPU}` | HPA |
| `ingress.{enabled,host,tls,className,annotations}` | Ingress |
| `persistence.{enabled,size,storageClass}` | PVC |
| `config.*` | ConfigMap data |
| `networkPolicy.enabled` | NetworkPolicy |
| `podDisruptionBudget.minAvailable` | PDB |
| `env` | maps to the deployment platform config profiles (dev/prod/offline) |

The `values-*.yaml` files mirror the deployment-platform profiles exposed by
`src/platform/deployment` (`development`, `production`, `offline`), so the chart
and the in-app deployment manager stay consistent.
