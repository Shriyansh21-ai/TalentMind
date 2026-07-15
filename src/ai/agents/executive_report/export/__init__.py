"""Export engine facade (Module 11).

One entry point for turning an :class:`ExecutiveHiringReport` into a downloadable
artefact in any supported format (PDF, DOCX, HTML, PPTX), plus the named
"packets" executives ask for (Executive Summary, Candidate Report, Committee
Report, Interview Packet, Recruiter Report, Hiring Manager Report). Every packet
is just a template + format combination over the *same* structured report — no
analysis is ever duplicated (Module 15). All renderers are dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from src.ai.agents.executive_report.branding import DEFAULT_BRAND, Brand
from src.ai.agents.executive_report.export import docx as _docx
from src.ai.agents.executive_report.export import html as _html
from src.ai.agents.executive_report.export import pdf as _pdf
from src.ai.agents.executive_report.export import ppt as _ppt
from src.ai.agents.executive_report.renderer import ReportDocument, build_document
from src.ai.agents.executive_report.schemas import ExecutiveHiringReport
from src.ai.agents.executive_report.templates import get_template

# format key -> (renderer, mime type, file suffix)
_EXPORTERS: Dict[str, Tuple[Callable[[ReportDocument], bytes], str, str]] = {
    "pdf": (_pdf.render, "application/pdf", "pdf"),
    "docx": (
        _docx.render,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ),
    "html": (_html.render, "text/html", "html"),
    "pptx": (
        _ppt.render,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pptx",
    ),
}

FORMATS: List[str] = list(_EXPORTERS.keys())


@dataclass(frozen=True)
class Packet:
    """A named, ready-to-send report packet (template + default format)."""

    key: str
    name: str
    template: str
    default_format: str = "pdf"


# The named packets a recruiter/executive can request directly (Module 11).
PACKETS: Dict[str, Packet] = {
    "executive_summary": Packet("executive_summary", "Executive Summary", "executive", "pdf"),
    "candidate_report": Packet("candidate_report", "Candidate Report", "hr", "pdf"),
    "committee_report": Packet("committee_report", "Committee Report", "committee", "pdf"),
    "interview_packet": Packet("interview_packet", "Interview Packet", "engineering_manager", "pdf"),
    "recruiter_report": Packet("recruiter_report", "Recruiter Report", "recruiter", "pdf"),
    "hiring_manager_report": Packet("hiring_manager_report", "Hiring Manager Report", "engineering_manager", "pdf"),
    "cto_report": Packet("cto_report", "CTO Report", "cto", "pdf"),
    "ceo_report": Packet("ceo_report", "CEO Report", "ceo", "pdf"),
}


def export_document(document: ReportDocument, fmt: str = "pdf") -> bytes:
    """Render a prepared :class:`ReportDocument` to ``fmt`` bytes."""
    key = (fmt or "pdf").strip().lower().lstrip(".")
    if key == "ppt":
        key = "pptx"
    if key not in _EXPORTERS:
        raise ValueError(f"Unsupported export format {fmt!r}. Supported: {FORMATS}.")
    renderer, _mime, _suffix = _EXPORTERS[key]
    return renderer(document)


def export_report(
    report: ExecutiveHiringReport,
    fmt: str = "pdf",
    template: str = "executive",
    *,
    brand: Brand = DEFAULT_BRAND,
) -> bytes:
    """Build the document for ``template`` and render it to ``fmt`` bytes."""
    tmpl = get_template(template)
    document = build_document(report, tmpl.section_ids, brand=brand, audience=tmpl.audience)
    return export_document(document, fmt)


def export_packet(
    report: ExecutiveHiringReport,
    packet: str,
    *,
    fmt: str = "",
    brand: Brand = DEFAULT_BRAND,
) -> Tuple[bytes, str, str]:
    """Render a named packet. Returns ``(bytes, mime_type, filename)``."""
    spec = PACKETS.get((packet or "").strip().lower())
    if spec is None:
        raise ValueError(f"Unknown packet {packet!r}. Known: {sorted(PACKETS)}.")
    chosen = (fmt or spec.default_format).strip().lower().lstrip(".")
    if chosen == "ppt":
        chosen = "pptx"
    data = export_report(report, chosen, spec.template, brand=brand)
    _renderer, mime, suffix = _EXPORTERS[chosen]
    filename = f"{report.candidate_id}_{spec.key}.{suffix}"
    return data, mime, filename


def mime_for(fmt: str) -> str:
    """Return the MIME type for a format key."""
    key = (fmt or "pdf").strip().lower().lstrip(".")
    if key == "ppt":
        key = "pptx"
    return _EXPORTERS.get(key, _EXPORTERS["pdf"])[1]


def suffix_for(fmt: str) -> str:
    """Return the file suffix for a format key."""
    key = (fmt or "pdf").strip().lower().lstrip(".")
    if key == "ppt":
        key = "pptx"
    return _EXPORTERS.get(key, _EXPORTERS["pdf"])[2]
