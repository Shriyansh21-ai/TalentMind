---
name: faiss-torch-import-order
description: TalentMind app.py must import faiss before torch/sentence-transformers or it segfaults on Windows
metadata:
  type: project
---

In TalentMind, `app.py` must `import faiss` as its very first import (before
streamlit and before anything that pulls in torch / sentence-transformers, e.g.
`src.scoring.hybrid_score` → `src.semantic.semantic_score`). On Windows the
reverse OpenMP load order **segfaults the process at import time** (exit 139),
including under `streamlit run`. Bare `import torch, faiss` in isolation works,
but the app's specific interleaved import chain crashes without faiss loaded
first. Verified fix: `import faiss  # noqa: F401` at the top of `app.py`.

**Why:** faiss and torch each bundle their own OpenMP runtime; whichever
initializes first wins, and this import chain only survives faiss-first.
**How to apply:** never reorder that top import; if adding a new entry point,
import faiss first there too.
