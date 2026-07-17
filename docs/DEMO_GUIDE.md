# TalentMind — Demo Guide

A guided script for demonstrating TalentMind to recruiters, executives, and engineering audiences.
The platform is **offline and deterministic**, so every step is reproducible and requires no
network (after the one-time model download). Total runtime for the full script is ~20 minutes;
each flow stands alone.

> **Setup:** `streamlit run app.py`, then have a job description file and a populated
> `data/raw/candidates.jsonl` ready. Use the sidebar **Workspace** selector to switch flows.

---

## 1. Recruiter workflow (~4 min)

**Goal:** show explainable ranking that beats keyword matching.

1. Open **Recruiter Console**. Upload the JD, click **Rank**.
2. Point out the **Job Profile dashboard** — parsed role, complexity, hiring difficulty.
3. Scroll the ranked candidates; open a top card and highlight the **10-component score
   breakdown** and the plain-English **reasons**.
4. Run a natural-language **recruiter search** (e.g. *"ML engineer with RAG experience"*) to show
   FAISS semantic retrieval.
5. Export to CSV/JSON.

**Talking point:** "Every number traces to a signal — no black box."

## 2. Copilot workflow (~3 min)

**Goal:** conversational access with grounded answers.

1. Open **AI Recruiter Copilot**.
2. Ask: *"Compare the top two candidates and flag any risks."*
3. Show that the answer cites **evidence sources** and a **confidence note**, and that it invoked
   deterministic tools (comparison, risk) rather than free-forming.

**Talking point:** "The copilot can only say what a deterministic engine computed."

## 3. Committee workflow (~4 min)

**Goal:** the flagship multi-agent decision.

1. Open **AI Hiring Committee**, pick a candidate, choose a **mode** (balanced).
2. Walk through the **7 independent reviewers** — each reads one evidence slice.
3. Show the **evidence-weighted consensus** (not a majority vote), any **conflicts** with root
   cause, and the **chair's decision**.
4. Re-run in **conservative** mode to show the deterministic stance bias.

**Talking point:** "Three thinly-supported agreements don't manufacture a strong consensus."

## 4. Executive workflow (~2 min)

**Goal:** boardroom-ready output.

1. Open **Executive Hiring Report**, select a candidate.
2. Show the one-page executive narrative and the **export** options (docx/html/pdf/ppt).

## 5. Governance workflow (~4 min)

**Goal:** defensible, compliant hiring.

1. **Compensation Governance** — show a defensible pay *range* (never a fixed prediction) with
   justification for HR/Finance/Legal.
2. **Pay Equity Guardian** — show internal-fairness checks; note it is *data-gated* and marks
   unavailable data honestly (no bias/legal conclusions).
3. **Hiring Compliance** — show workflow/approval/documentation checks.
4. **Hiring Audit** — show the reconstructed decision journey separating observed facts, inferred
   insights, AI recommendations, and human decisions.

**Talking point:** "Governance agents never give legal advice or fabricate a conclusion."

## 6. Hiring Intelligence workflow (~2 min)

**Goal:** organizational analytics.

1. Open **Hiring Intelligence**. Show cohort-level hiring health, bottlenecks, trends, KPIs.
2. Emphasize it operates on **cohorts, never ranking individuals**, and marks unavailable metrics
   honestly.

## 7. Platform tour (~3 min, technical audiences)

1. **Platform Administration** — multi-tenant orgs, roles, licenses, seats, audit (demo tenants).
2. **Integration Marketplace** — the HRIS/ATS provider catalogue (offline reference providers).
3. **Runtime Operations** — jobs/workers/health/resilience.
4. **Security & Operations Center** — identity, RBAC+ABAC, hash-chained audit, compliance.

**Talking point:** "An additive enterprise platform, isolated from the hiring engines and enforced
by architecture tests."

---

## Suggested timings

| Audience | Flows | Duration |
|---|---|---|
| Recruiters | 1, 2, 3 | ~11 min |
| Executives | 1, 3, 4, 6 | ~12 min |
| Engineering / platform | 1, 3, 7 | ~11 min |
| Full walkthrough | all | ~22 min |
