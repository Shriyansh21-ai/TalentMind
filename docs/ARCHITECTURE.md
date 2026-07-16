# TalentMind — Architecture Index, Project Map & Module Registry

TalentMind is a layered platform. The **Phase 1–5 business core** (hiring,
scoring, semantic, intelligence, AI agents) is stable and unchanged. **Phase 6**
adds five strictly-additive enterprise platforms under `src/platform/`, none of
which import the business core (mechanically enforced by architecture tests).

---

## 1. Layered architecture

```
   ┌──────────────────────────────────────────────────────────────────────┐
   │  Presentation:  app.py (Streamlit) · src/ui/*                          │
   ├──────────────────────────────────────────────────────────────────────┤
   │  Phase 6 — Enterprise Platforms (additive · offline · deterministic)   │
   │                                                                        │
   │   src/platform/            (M1) Enterprise SaaS foundation             │
   │   src/platform/integrations (M2) Integration platform                  │
   │   src/platform/runtime      (M3) Runtime / scalability                 │
   │   src/platform/security     (M4) Security / governance / observability │
   │   src/platform/deployment   (M5) Deployment / release / production     │
   ├──────────────────────────────────────────────────────────────────────┤
   │  Phase 1–5 — Business Core (UNCHANGED)                                 │
   │   scoring · semantic · intelligence · hiring · recruiter · pipeline ·  │
   │   reasoning · ingestion · insights · comparison · talent_pool ·        │
   │   interview · filtering · dashboard · llm · ai · models · utils        │
   └──────────────────────────────────────────────────────────────────────┘
```

**Dependency direction:** Presentation → Phase 6 platforms → (nothing in the
business core). The business core has **no** dependency on Phase 6. Phase 6
platforms depend only on `src/platform/common` and, where DRY dictates, on each
other (e.g. security reuses the M1 RBAC grammar and the M2 secret seam; runtime
publishes onto the M2 event bus).

---

## 2. Project map

```
TalentMind/
├── app.py                     Streamlit entry point (thin orchestrator)
├── rank.py                    CLI ranking entry point
├── requirements.txt           runtime dependencies
├── requirements-dev.txt       test-only dependencies
├── pyproject.toml             tooling + package metadata
├── Dockerfile                 multi-stage production image
├── docker-compose*.yml        base / dev / prod compose
├── k8s/                       Kubernetes manifests (+ Helm structure doc)
├── .github/workflows/         CI + Release pipelines
├── docs/                      developer, architecture, DR, install guides
├── tests/                     full test suite (unit · arch · UI AppTests)
└── src/
    ├── platform/              Phase 6 enterprise platforms (see registry)
    ├── ai/                    AI agents & multi-agent orchestration
    ├── scoring/ semantic/ intelligence/ hiring/ recruiter/ pipeline/
    ├── reasoning/ ingestion/ insights/ comparison/ talent_pool/
    ├── interview/ filtering/ dashboard/ llm/ models/ utils/
    └── ui/                    Streamlit workspaces
```

---

## 3. Module registry — `src/platform`

| Package | Milestone | Responsibility | Composition root |
|---|---|---|---|
| `common` | M1 | Base models, errors, ids, clock, repository | — |
| `organizations` · `tenancy` · `auth` · `rbac` · `workspaces` · `config` · `subscription` · `notifications` · `audit` · `api` · `storage` · `developer` | M1 | Multi-tenant SaaS foundation | `bootstrap.build_platform` |
| `integrations` | M2 | HRIS/ATS/calendar/comms/docs providers, API gateway, webhooks, event bus, sync, marketplace, SDK | `integrations.build_integration_platform` |
| `runtime` | M3 | Jobs, workers, execution, cache, health, load, resilience, resources, runtime events, observability | `runtime.build_runtime_platform` |
| `security` | M4 | Identity, RBAC+ABAC, audit, secrets, observability, monitoring, governance, compliance, threat, config governance, incidents, analytics | `security.build_security_platform` |
| `deployment` | M5 | Deployment manager, configuration, backup, release, validation, benchmark, packaging, health check | `deployment.build_deployment_platform` |

All five are reachable from the single facade:

```python
from src.platform.bootstrap import build_platform
p = build_platform()
p.integrations   # M2
p.runtime        # M3
p.security       # M4
p.deployment     # M5
```

---

## 4. Dependency map (Phase 6, no cycles)

```
   common ◀── every platform package
      ▲
      │
   organizations ◀ tenancy ◀ auth · rbac · workspaces · config · subscription …
      ▲
      │  (reused, never modified)
   integrations ──events.bus──▶ runtime.events        (runtime publishes here)
      ▲                              │
      │ (secret seam reused)         │
   security ──rbac.matches (reused)──┘
      ▲
      │ (encryption/provider seam reused)
   deployment ── validation probes modules via find_spec (no import cycle)
```

Cross-platform reuse is deliberate and one-directional (no cycles):
- **security → rbac** (`matches`, `Role`) and **security → integrations.secrets**
  (encryption seam).
- **runtime → integrations.events** (shared enterprise event bus).
- **deployment → deployment.\*** only; it probes other packages by name
  (`importlib.util.find_spec`) so it never imports them at module load.

---

## 5. Cross-cutting conventions

- **Models / Repository / Service** per module; interfaces (Protocols/ABCs)
  before implementations (Clean Architecture, DIP).
- **Tenant isolation** enforced at the `InMemoryRepository` boundary.
- **Injected `Clock`** everywhere — deterministic, no wall-clock sleeps.
- **Lazy DI** via `Container`; each service built at most once.
- **Additive rule** — `src/platform/*` never imports Phase 1–5 business packages
  (guarded by `test_*_never_imports_business_logic`).

See `DEVELOPER_GUIDE.md` for coding standards, extension and contribution flow.
