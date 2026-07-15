# Memory Index

- [faiss-torch-import-order](faiss-torch-import-order.md) — app.py must import faiss first or it segfaults on Windows
- [phase2-m2-workspace](phase2-m2-workspace.md) — Enterprise Workspace architecture, shared-insights pattern, and the pytest command
- [phase3-m1-ai-platform](phase3-m1-ai-platform.md) — AI Platform (src/ai): provider-agnostic agents, offline-by-default, HiringAnalystAgent
- [phase3-m2-copilot](phase3-m2-copilot.md) — AI Recruiter Copilot: tool layer (src/ai/tools) + copilot core (src/ai/copilot)
- [phase3-m3-orchestration](phase3-m3-orchestration.md) — Multi-Agent Orchestration Framework (src/ai/orchestration): planner/engine/delegation/registry; future agents plug in via adapters
- [phase4-m1-resume-agent](phase4-m1-resume-agent.md) — ResumeAnalystAgent (src/ai/agents/resume): first business agent; resume quality only; score-free schema constraint
- [phase4-m2-jd-agent](phase4-m2-jd-agent.md) — JDAnalystAgent (src/ai/agents/jd): second business agent; JD quality/intent only; token-boundary tech matching
- [phase4-m3-hiring-committee](phase4-m3-hiring-committee.md) — AI Hiring Committee (src/ai/committee): flagship multi-agent decision engine; parallel reviews via workflow engine; evidence-weighted consensus
- [phase4-m5-interview-studio](phase4-m5-interview-studio.md) — InterviewStudioAgent (src/ai/agents/interview_studio): final hiring-lifecycle agent; personalized interview packages; reuses committee gather_evidence
- [phase5-m1-compensation](phase5-m1-compensation.md) — CompensationGovernanceAgent (src/ai/agents/compensation): compensation transparency/audit system; defensible ranges not predictions; HRIS-ready no connectors
- [phase5-m2-pay-equity](phase5-m2-pay-equity.md) — PayEquityGuardianAgent (src/ai/agents/pay_equity): internal fairness/governance; reuses comp agent; data-gated (unavailable without HRIS); no legal conclusions
- [phase5-m3-compliance](phase5-m3-compliance.md) — HiringComplianceAgent (src/ai/agents/compliance): hiring workflow governance/compliance; reuses whole chain via pay equity; data-gated; no legal advice
- [phase5-m4-audit](phase5-m4-audit.md) — HiringAuditAgent (src/ai/agents/audit): audit & explainability; reconstructs decision journey; reuses whole chain via compliance; human-vs-AI never blurred; no fabrication
- [phase5-m5-hiring-intelligence](phase5-m5-hiring-intelligence.md) — HiringIntelligenceAgent (src/ai/agents/hiring_intelligence): org-level workforce analytics; cohort-based (cheap insights_fn); data-gated; never ranks individuals
