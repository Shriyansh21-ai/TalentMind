# TalentMind — Operations Guide

Day-2 operations for a running TalentMind deployment. TalentMind is offline and deterministic by
default, so most operational concerns reduce to process health, disk hygiene, and configuration.
For recovery playbooks see [`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md); for the runtime platform
internals see [`RUNTIME.md`](RUNTIME.md).

---

## 1. Health checks

| Layer | Check |
|---|---|
| Container | `HEALTHCHECK` on `http://localhost:8501/_stcore/health` (defined in the `Dockerfile`). |
| Kubernetes | Liveness/readiness probes in `k8s/05-deployment.yaml`. |
| Runtime platform | `p.runtime.health` (`HealthAggregator`) aggregates platform / workers / queue / cache / integration / ai_platform / database checks. |
| AI platform | `get_platform_status()` in `src/ai/services/hiring_analyst_service.py`. |
| Installation | `verify_installation()` (`src/platform/deployment/packaging.py`). |

```python
from src.platform.bootstrap import build_platform
p = build_platform()
print(p.runtime.health.aggregate())     # component health snapshot
```

---

## 2. Logs & telemetry

| Path | Contents |
|---|---|
| `logs/ai_telemetry.jsonl` | Append-only AI agent telemetry (one JSON event per line). |
| `logs/` | Application logs. |

AI telemetry is also available in-process:

```python
from src.ai.services.hiring_analyst_service import recent_telemetry
recent_telemetry()      # last N events from the in-memory ring buffer
```

The telemetry logger **never raises** — a logging failure cannot break a request.

---

## 3. Cache management

The AI file cache lives in `data/ai_cache/` (one JSON file per key). It is safe to delete at any
time — reads never raise, so a missing entry is simply a cache miss.

```bash
rm -rf data/ai_cache/*      # clear the AI cache (results recompute deterministically)
```

Cache keys incorporate agent version, prompt version, provider, and model, so bumping any of these
naturally invalidates stale entries. To force a single recompute, pass
`AgentConfig(force_refresh=True)`.

The runtime platform's `BackgroundServiceManager` schedules recurring maintenance (cache cleanup
300s, telemetry cleanup 600s, health polling 30s) when the runtime platform is driven.

---

## 4. Disk hygiene

| Directory | Growth | Action |
|---|---|---|
| `data/ai_cache/` | grows with distinct analyses | periodically clear |
| `logs/` | grows with telemetry | rotate/truncate |
| `outputs/` | `rank.py` exports | archive or delete |

All are git-ignored and safe to prune.

---

## 5. Scaling

- **Horizontal** — the Streamlit app is stateless per request; scale replicas behind the ingress
  (`k8s/08-hpa.yaml` provides an HPA). Persist shared runtime state via the storage interfaces if
  you introduce cross-replica coordination.
- **Model memory** — the sentence-transformer model is loaded once per process (Streamlit
  `@st.cache_resource`). Size pods with ~4–8 GB RAM when the ML stack is active.
- **Runtime platform** — `WorkerPool.scale_to(n)` and the load/backpressure controllers model
  horizontal scaling deterministically; wire them to real workers when you add a job backend.

---

## 6. Configuration changes

Runtime configuration is via environment variables (see [`CONFIGURATION.md`](CONFIGURATION.md)).
Per-tenant feature flags/licenses are managed through `ConfigurationService`, and the security
platform provides a **versioned config-governance workflow** with approvals and rollback
(`ConfigurationGovernanceService`: `propose_change` → `approve`/`reject` → `rollback`).

---

## 7. Audit & compliance operations

- Verify audit integrity: `p.audit.verify_chain(tenant_id)` (and the security platform's
  `EnterpriseAuditService.verify_chain`). A `False` result indicates tampering.
- Apply retention: `EnterpriseAuditService.apply_retention(...)`.
- Collect compliance evidence: `p.security.compliance.collect_evidence(standard)` and
  `gap_analysis(standard)` for GDPR / SOC 2 / ISO 27001 / HIPAA / PCI-DSS / AI-governance.
