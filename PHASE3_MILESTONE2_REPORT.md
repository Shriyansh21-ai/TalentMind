# TalentMind — Phase 3 / Milestone 2 Report
## AI Recruiter Copilot

**Status:** ✅ Complete and verified — the app boots (Streamlit `AppTest`), all
imports resolve, the Copilot works with real candidate data via a repository
seam, conversation + tool planning + tool execution all work, and there are **no
regressions** (82 automated tests passing).

This milestone builds the **first enterprise AI application** on top of the Phase-3
AI Platform: an **AI Recruiter Copilot** that understands recruiter intent,
selects the *right* deterministic tools, reasons over their structured outputs,
and produces professional, evidence-based recruiter answers — plus follow-ups and
one-click actions. It is not a chatbot: every fact originates from an existing
deterministic engine, surfaced through a typed tool.

---

## 1. Principles honoured

- **Never replace the engines — orchestrate them.** Ranking, semantic search,
  intelligence, timeline, risk, recommendation and interview engines are wrapped
  as **tools**; the copilot calls them, never reimplements them.
- **The LLM sees only structured tool outputs** — never raw resumes or raw JSON
  dumps. Offline it uses a deterministic composer (no hallucination possible).
- **Minimal tools per request.** A declarative intent→tools policy means the
  copilot never runs every tool (Module 5).
- **Deterministic where it should be.** Intent detection, planning, follow-ups
  and actions are all deterministic and unit-tested. Only the narration is AI.
- **SOLID / DI throughout.** The controller, planner, tools and runner are all
  injected and testable with a synthetic repository — no dataset, no FAISS, no
  network required to test.
- **Auto-discovery.** New tools and agents register themselves; the copilot picks
  them up by name with no controller change.

---

## 2. Architecture

### 2.1 System view

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     DETERMINISTIC ENGINES (unchanged)                       │
│  Ranking · Semantic/FAISS · CrossEncoder · Candidate Intelligence ·        │
│  Timeline · Risk · Hiring Recommendation · Interview · Comparison ·        │
│  Pipeline · Dashboard · Skill-gap · Explainability                         │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │ wrapped 1:1 as typed Tools
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          TOOL LAYER  (src/ai/tools)                         │
│   BaseTool · ToolRegistry · ToolRunner · ToolContext                       │
│   CandidateRepository (DI seam → data + FAISS, or synthetic in tests)      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    RECRUITER COPILOT  (src/ai/copilot)                      │
│                                                                            │
│   RecruiterCopilot.ask(session, message)                                   │
│     1. ConversationManager → session (history + state)                     │
│     2. IntentClassifier    → IntentResult   (pattern registry, no if-else) │
│     3. CopilotPlanner      → CopilotPlan     (minimal tools + inputs)      │
│     4. ToolRunner          → [ToolResult]    (deterministic engine calls)  │
│     5. AI Platform (Phase 3 M1) ── RecruiterCopilotAgent ─────────────────┐│
│          structured tool outputs → CopilotResponse (validated, safe)      ││
│     6. ResponseBuilder     → CopilotTurn (answer + follow-ups + actions   ││
│                              + tool visibility)                            ││
│   ─────────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────┬──────────────────────────────────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │  UI: AI Recruiter Copilot│  chat · context · tool cards
                    │  page (src/ui)           │  · actions · indicators
                    └──────────────────────────┘
```

### 2.2 Folder structure

```
src/ai/tools/                    # Tool layer (Module 4) — platform-level, reusable
├── base.py                      # BaseTool, ToolMetadata, ToolResult, ToolContext,
│                                #   CandidateRepository (DI seam)
├── registry.py                  # ToolRegistry + ToolRunner (+ default `registry`)
├── provider.py                  # InMemoryCandidateRepository (data / test wiring)
├── search_tools.py              # FAISSSearchTool, CandidateSearchTool, SkillGapTool
├── intelligence_tools.py        # Intelligence/Timeline/Risk/Recommendation/
│                                #   Interview/Explainability tools
├── workspace_tools.py           # Comparison/Pipeline/Dashboard tools
└── builtin.py                   # registers all built-in tools

src/ai/copilot/                  # Copilot core (Modules 1-3, 5) — UI-independent
├── models.py                    # Intent, Entities, IntentResult, CopilotPlan,
│                                #   CopilotAction, CopilotTurn, Message
├── state.py                     # ConversationState (working context)
├── history.py                   # ConversationHistory
├── session.py                   # CopilotSession + SessionStore
├── conversation.py              # ConversationManager
├── planner.py                   # IntentClassifier + CopilotPlanner
├── tool_selector.py             # intent → minimal tool set (declarative)
├── response_builder.py          # follow-ups + actions + CopilotTurn assembly
└── controller.py                # RecruiterCopilot (lifecycle orchestrator)

src/ai/agents/recruiter_copilot.py   # RecruiterCopilotAgent + deterministic composer
src/ai/schemas/copilot_response.py   # CopilotResponse (score-free)
src/ai/prompts/templates/recruiter_copilot_{system,user}.v1.md

src/ui/copilot_page.py           # AI Recruiter Copilot page (Modules 8-10)
app.py                           # (modified) minimal sidebar workspace switch
```

---

## 3. Copilot lifecycle

```
recruiter message
      │
      ▼
[ConversationManager] get_or_create(session)  ── history + working state
      │
      ▼
[IntentClassifier] classify ─────────────►  IntentResult {intent, confidence,
      │   (weighted keyword pattern registry — no if-else chains)   entities}
      ▼
[CopilotPlanner] plan ───────────────────►  CopilotPlan {ordered (tool, input)}
      │   (intent→tools map + contextual candidate/comparison resolution)
      ▼
[ToolRunner] run_many ───────────────────►  [ToolResult]  (calls real engines
      │                                        via ToolContext + repository)
      ▼
update ConversationState (focus candidate, comparison set, last search)
      │
      ▼
[AI Platform] AgentRunner.run(RecruiterCopilotAgent,
      │        {intent, message, tool_outputs}) ──► CopilotResponse
      │        (cache · retries · validation · safety · offline composer)
      ▼
[ResponseBuilder] build_turn ────────────►  CopilotTurn {answer, reasoning,
      │   + deterministic follow-ups (3)      tools_used, follow_ups, actions,
      │   + deterministic actions             evidence, provider, latency}
      ▼
[ConversationManager] record → history      returned to UI
```

### Planning example (Module 5)

> "Why is CAND_A better than CAND_B?" → intent **Compare Candidates** →
> tools **[comparison, risk, timeline]** — *not* all twelve tools.

---

## 4. Tool calling

Each deterministic engine is a `BaseTool` with `metadata`, `validate()` and
`execute()`. `ToolRunner.run()` wraps execution with timing + uniform error
handling, returning a `ToolResult` (`output`, `summary`, `evidence_sources`,
`confidence`, `latency_ms`). A failing tool degrades to a failed result — the
copilot still reasons over whatever succeeded.

Twelve built-in tools: `faiss_search`, `candidate_search`, `skill_gap`,
`candidate_intelligence`, `timeline`, `risk`, `recommendation`, `interview`,
`explainability`, `comparison`, `pipeline`, `dashboard`.

**Adding a tool:** implement `BaseTool`, register it in `builtin.py` (or its own
module), and map an intent to it in `tool_selector.py`. No controller change.

---

## 5. Conversation & state management

- `ConversationHistory` — ordered user/assistant messages.
- `ConversationState` — the working set: `current_candidate`, `current_comparison`,
  `current_jd`, `current_pipeline_candidate`, `current_filters`,
  `last_search_results`. This lets follow-ups resolve contextually ("analyze
  **that** candidate", "compare **them**").
- `CopilotSession` bundles history + state under an id; `SessionStore` holds them;
  `ConversationManager` is the single coordinator (SRP).

---

## 6. Response generation (Module 6) & safety (Module 11)

The `RecruiterCopilotAgent` runs on the Phase-3 AI Platform and receives **only**
the structured tool outputs. Safety is inherited + reinforced:

- **No fabrication** — offline the composer only restates tool evidence.
- **No contradiction** — scores/recommendations come from the tools; the copilot
  narrates them.
- **No scores emitted** — `CopilotResponse` is score-free by design (the platform
  `SafetyGuard` enforces this structurally).
- **Evidence cited** — every turn lists the engines it relied on.
- **Uncertainty stated** — thin/high-risk evidence produces an explicit
  confidence caveat.

---

## 7. Follow-ups (Module 7) & actions (Module 10)

Both are **deterministic**. `response_builder.suggest_follow_ups(intent)` returns
exactly three contextual questions; `suggest_actions(plan)` returns relevant
recruiter actions (move to shortlist, compare, interview plan, open profile, view
risk/timeline, hiring report) with the resolved candidate/comparison ids. Actions
integrate with existing modules — e.g. *Move to Shortlist* calls the Phase-2
pipeline engine directly; navigational actions become in-conversation follow-ups.

---

## 8. UI (Modules 8-10)

`src/ui/copilot_page.py` renders an enterprise chat workspace: conversation panel
(`st.chat_message` / `st.chat_input`), a **current-context** sidebar (focus
candidate, comparison set, provider/model/cache indicators, turn count),
**tool-visibility** cards (tools used, per-tool confidence, latency, evidence
sources, reasoning summary), **suggested follow-ups**, and **action buttons**.
`app.py` gained only a small sidebar workspace switch — the console is untouched.
The candidate repository is built lazily on first message, so the page renders
instantly and never loads the dataset just to show the chat.

---

## 9. Performance (Module 12)

- **Minimal tools** per request (intent-scoped selection).
- **Reuses every cache:** the AI Platform response cache (keyed by intent +
  message + tool-output signature), the deterministic engines' caches (via the
  injected `insights_fn` = the UI's cached `get_insights`), and lazy repository
  construction.
- **Offline-fast default** — the deterministic composer needs no network.

---

## 10. Verification (Module 14)

| Check | Result |
|---|---|
| Compile `src/ai` + UI + app (`compileall`) | ✅ |
| Imports resolve / no circular deps (faiss-before-torch preserved) | ✅ |
| Intent detection (10 intents + entities + default) | ✅ |
| Tool selection (minimal sets) | ✅ |
| Planner (candidate/comparison resolution, skip-without-candidate) | ✅ |
| Conversation + state | ✅ |
| Response builder (3 follow-ups, actions) | ✅ |
| Tool registry + runner (register, unknown-tool, execution) | ✅ |
| Controller end-to-end offline (search/analyze/contextual/general) | ✅ |
| Copilot page renders + answers a message (AppTest) | ✅ |
| App boots; no Phase 1/2/3-M1 regressions | ✅ |
| **Total** | **82 tests passing** |

Run: `pytest tests/ -p no:faulthandler`
(`-p no:faulthandler` silences a benign faiss/torch OpenMP shutdown traceback on
Windows; exit code is 0.)

---

## 11. Future vision — adding agents/tools without redesign

The copilot discovers tools by name and the platform discovers agents by name, so
future milestones plug in with minimal work:

- **New tool** → implement `BaseTool`, register in `builtin.py`, add to an intent
  in `tool_selector.py`. The copilot uses it immediately.
- **New agent** (`ResumeAnalystAgent`, `JDAnalystAgent`, `InterviewPlannerAgent`,
  `SalaryAdvisorAgent`, `OfferAdvisorAgent`, `HiringCommitteeAgent`,
  `ExecutiveReportAgent`, `WorkforcePlanningAgent`) → subclass `BaseAgent`,
  register a composer + templates. The copilot could route to it as a "tool"
  (an agent-as-tool wrapper is a natural next step).
- **New intent** → one entry in the pattern registry + one in the tool map.
- **Durable memory / multi-agent orchestration** → the `ConversationManager` and
  `AgentRegistry` seams are already in place; no controller redesign needed.

---

## 12. Extension points summary

| Want to… | Change |
|---|---|
| Add a recruiter capability | new `BaseTool` + `tool_selector` entry |
| Add a new intent | pattern registry + tool map (2 data edits) |
| Swap the LLM provider | `TALENTMIND_AI_PROVIDER` env var (no code) |
| Add durable memory | implement `BaseMemory`; wire in `ConversationManager` |
| Change follow-up/action UX | edit `response_builder` (deterministic maps) |
| Route to a specialist agent | wrap the agent as a tool; register it |

The result is an enterprise AI assistant that collaborates with recruiters using
deterministic intelligence, structured tool outputs and professional reasoning —
the first application on a platform built to host many more.
