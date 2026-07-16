# TalentMind — Disaster Recovery (Module 10)

Recovery procedures, playbooks and checklists for the TalentMind platform.
TalentMind is **offline and deterministic by default**, so most failure modes
are recoverable by redeploying a known-good image + configuration and restoring
backups. Objectives: **RTO ≤ 60 min**, **RPO ≤ 15 min**.

The in-app deployment platform (`src/platform/deployment`) plans and validates
these operations: `DeploymentManager` (deploy/rollback), `BackupManager`
(backup/restore/recovery plans), `ProductionValidator` (readiness). Each
playbook below maps to those services.

---

## Architecture of recovery

```
        ┌──────────────── Detection ────────────────┐
        │  Monitoring alerts · Health probes · Audit │
        └───────────────────┬────────────────────────┘
                            ▼
        ┌──────────── Classify (Incident) ───────────┐
        │  IncidentService: severity · owner · timeline│
        └───────────────────┬─────────────────────────┘
                            ▼
   ┌────────── Recover (per-subsystem playbook) ──────────┐
   │ redeploy image → restore config/backups → warm cache │
   │ → validate restores → ProductionValidator → resume   │
   └───────────────────┬───────────────────────────────────┘
                       ▼
        ┌──────────── Verify & Report ───────────────┐
        │ readiness score = 1.0 · recovery_report()   │
        └──────────────────────────────────────────────┘
```

---

## Playbook 1 — Platform failure (total outage)

**Symptoms:** app unreachable; readiness probes failing across all pods.

**Checklist:**
1. Declare incident (`IncidentService.open_incident`, severity=CRITICAL).
2. Confirm image + tag of last known-good release (`ReleaseManager.latest`).
3. Redeploy: `kubectl rollout undo deployment/talentmind -n talentmind`
   (or `DeploymentManager.rollback(deployment_id)`).
4. Restore configuration backup (`BackupManager.restore` for `CONFIGURATION`).
5. Restore metadata + audit backups.
6. Validate restores (`BackupManager.recovery_report` → `all_valid == True`).
7. Run `ProductionValidator.validate()` → require `ready == True`.
8. Resume traffic; monitor for 30 min; resolve incident with root cause.

---

## Playbook 2 — Worker failure (background jobs stuck)

**Symptoms:** queue depth climbing; jobs not completing; worker heartbeats stale.

**Checklist:**
1. Inspect worker health (`runtime.workers.check_health()`).
2. Drain unhealthy workers (`WorkerPool.drain`) and scale replacements
   (`WorkerPool.scale_to(n)`).
3. Requeue in-flight jobs: failed jobs auto-retry per `RetryPolicy`; verify via
   `JobManager.stats(tenant)`.
4. Confirm queue drains; check backpressure (`LoadManager.admit`).
5. If systemic, roll workers to the previous image.

---

## Playbook 3 — Cache failure

**Symptoms:** elevated latency; cache hit-rate near zero; cache backend errors.

**Checklist:**
1. Cache is non-authoritative — the platform functions without it (cold reads).
2. Fail over to the in-memory provider (`MemoryCacheProvider`) or restart Redis.
3. Warm the cache (`CacheWarmer.warm(...)`) from source or backups.
4. Verify hit-rate recovers on the Runtime Operations dashboard.

---

## Playbook 4 — Integration failure (external system down)

**Symptoms:** connector health degraded; webhook deliveries dead-lettering.

**Checklist:**
1. Integrations are isolated — a failing provider never blocks the core app.
2. Inspect `integrations.manager.check_health(...)`; disable the failing
   integration (`disable`) to stop retries.
3. Dead-lettered webhooks are retained; replay with
   `WebhookService.retry(...)` once the endpoint recovers.
4. Re-enable and reconnect (`connect`); confirm health returns to HEALTHY.

---

## Playbook 5 — Runtime failure (execution engine / circuit open)

**Symptoms:** circuit breakers open; tasks failing fast; degraded throughput.

**Checklist:**
1. Inspect `LoadManager.snapshot()` — identify the open circuit.
2. Let the circuit recover (HALF_OPEN → CLOSED) after the recovery timeout, or
   restart the affected component.
3. Verify resilience recovery via runtime events (`runtime.events.history`).
4. Confirm health aggregator returns to HEALTHY.

---

## Playbook 6 — Security failure (breach / policy violation / audit tamper)

**Symptoms:** threat events (brute-force/escalation), policy violations, or a
broken audit chain (`EnterpriseAuditService.verify_chain == False`).

**Checklist:**
1. Open a CRITICAL incident; assign the security owner.
2. Contain: suspend affected identities (`IdentityManager.suspend`); revoke
   sessions (`deactivate`).
3. Rotate impacted secrets (`SecretManager.rotate`).
4. If the audit chain is broken, preserve the store for forensics and restore
   the last verified audit backup.
5. Run governance `enforce()` and a compliance `assess()` to confirm posture.
6. Produce a `threat_report` and incident report; document root cause.

---

## Recovery checklist (universal)

- [ ] Incident opened with severity + owner
- [ ] Last known-good version identified
- [ ] Image redeployed / rolled back
- [ ] Configuration restored and validated
- [ ] Data/metadata/audit backups restored and checksum-validated
- [ ] Caches warmed or rebuilt
- [ ] `ProductionValidator.validate().ready == True`
- [ ] Traffic resumed; monitored for 30 minutes
- [ ] Incident resolved with documented root cause and recovery report

---

## Backups

`BackupManager` backs up configuration, cache, logs, metadata and audit data;
each backup is checksummed and restore-validated. Bind a real `BackupProvider`
(S3/GCS/Azure) in production — the local provider is for offline/dev. Recommended
schedule: configuration + audit every 15 min (RPO), full metadata daily.
