"""Module 9 — Enterprise Audit Framework.

Platform-level, tamper-evident (hash-chained) auditing of authentication,
authorization, settings, workspace/permission/organization/configuration
changes — separate from the Phase 5 hiring audit. :meth:`verify_chain` detects
any tampering, supporting future compliance attestations.
"""

from __future__ import annotations

from src.platform.audit.models import AuditCategory, AuditEvent, AuditOutcome
from src.platform.audit.service import PlatformAuditService
from src.platform.audit.sink import AuditSink, InMemoryAuditSink

__all__ = [
    "AuditCategory",
    "AuditOutcome",
    "AuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "PlatformAuditService",
]
