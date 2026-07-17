"""Hiring documentation validation (Module 4).

Validates the presence of each required document by deriving it from the evidence
sources the upstream engines actually produced, plus an optional injected
document-management provider. **Missing documents are never fabricated** — an
absent artefact is reported Missing (or Requires Review when it is generatable on
demand but not confirmed filed) (Module 14).
"""

from __future__ import annotations

from typing import Any

from src.ai.agents.compliance.schemas import DocumentationReview, DocumentStatus
from src.ai.agents.compliance.templates import REQUIRED_DOCUMENTS


def validate_documentation(context: dict[str, Any], provider: Any) -> DocumentationReview:
    """Validate required-document presence (Module 4)."""
    sources = set(context.get("evidence_sources", []))
    provider_docs: dict[str, bool] = {}
    if provider is not None and getattr(provider, "is_available", lambda: False)():
        provider_docs = provider.get_documents(context.get("candidate_id", "")) or {}

    documents = []
    for doc in REQUIRED_DOCUMENTS:
        if doc.evidence_source and doc.evidence_source in sources:
            state, register = "Present", "Observed Evidence"
        elif doc.key in provider_docs:
            state = "Present" if provider_docs[doc.key] else "Missing"
            register = "Observed Evidence"
        elif not doc.evidence_source:
            # Generatable on demand (executive report / interview packet) but not
            # confirmed filed without a document-management source.
            state, register = "Requires Review", "Missing Information"
        else:
            state, register = "Missing", "Missing Information"
        documents.append(DocumentStatus(name=doc.name, state=state, register=register))

    return DocumentationReview(documents=documents)
