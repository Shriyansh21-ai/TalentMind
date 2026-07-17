# Contributing to TalentMind

Thank you for your interest in improving TalentMind. This guide covers the workflow, standards, and
architectural rules contributions must respect. It pairs with
[`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) (setup and extension points) and
[`ARCHITECTURE.md`](ARCHITECTURE.md) (design).

---

## Getting started

```bash
git clone https://github.com/your-org/talentmind.git
cd talentmind
python -m venv venv
source venv/bin/activate                 # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install ruff                         # linter/formatter (also used in CI)
```

Run the app with `streamlit run app.py` and the tests with `pytest -q`.

---

## Before you open a pull request

Run the same checks CI runs:

```bash
ruff format .            # format
ruff check .             # lint
pytest -q                # full test suite (761 tests)
```

All three must pass. The CI pipeline additionally runs mypy (scoped to `src/platform`), bandit,
pip-audit, a documentation-presence check, and a container build.

---

## Coding standards

- **Python 3.11+**, formatted and linted by **ruff** (line length 100; rules `E`, `F`, `W`, `I`,
  `B`, `UP` as configured in `pyproject.toml`).
- **Type hints** on public functions; **docstrings** on modules, classes, and public functions.
- **Pydantic** for data models; prefer explicit, immutable (frozen) config/dataclasses.
- Keep imports ordered (ruff `I`); no unused imports (ruff `F401`).

## Architectural rules (do not break these)

1. **Additive isolation** — `src/platform/*` must never import the Phase 1–5 business core. This is
   enforced by `test_*_never_imports_business_logic`. Platform packages depend only on
   `src/platform/common` and, where justified, each other.
2. **AI is score-free** — any new AI agent's output schema must contain no score/rating/percent
   field; the `SafetyGuard` enforces this at runtime.
3. **AI explains, never computes** — agents consume already-computed engine outputs and must not
   re-rank candidates or reimplement an engine. Copilot tools wrap existing engines.
4. **Offline-first** — new agents must register a deterministic composer so they work with the
   `local` provider and no network.
5. **Prompts are versioned Markdown**, never hard-coded in Python.
6. **Determinism** — no wall-clock `sleep`/`Date.now`-style nondeterminism in the platform; use the
   injected `Clock`.

## Adding features

- **New agent** — see [`ENTERPRISE_AGENTS.md`](ENTERPRISE_AGENTS.md#adding-a-new-agent).
- **New integration / provider** — see [`INTEGRATIONS.md`](INTEGRATIONS.md#adding-a-live-connector).
- Extend behind the existing interfaces rather than modifying working engines.

---

## Commit & PR conventions

- Write clear, imperative commit subjects (e.g. `Add pay-equity compression check`).
- Keep PRs focused; describe what changed and why, and note any test additions.
- Include tests for new behavior. Do not reduce coverage.
- Update the relevant docs and [`CHANGELOG.md`](CHANGELOG.md) when behavior or interfaces change.

## Reporting bugs & requesting features

Open an issue with reproduction steps (for bugs) or a clear use case (for features). For security
issues, follow the disclosure guidance in [`SECURITY.md`](SECURITY.md) rather than filing a public
issue.

## Code of Conduct

All participation is governed by the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
