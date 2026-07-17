"""Shared helpers for the export renderers.

Every exporter walks the same :class:`ReportDocument` IR. This module flattens a
section's typed blocks into a uniform ``(style, text)`` line stream so the PDF,
DOCX and PPTX renderers share one traversal (DRY), and provides escaping helpers.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.ai.agents.executive_report.renderer import Block, Section

# A line is (style, text). Styles: h2, h3, para, bullet, kv, note, metric.
Line = tuple[str, str]


def xml_escape(text: str) -> str:
    """Escape text for embedding in XML (OOXML) content."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def html_escape(text: str) -> str:
    """Escape text for embedding in HTML content."""
    return xml_escape(text).replace("'", "&#39;")


def pdf_escape(text: str) -> str:
    """Escape text for a PDF literal string and drop non-Latin-1 characters."""
    safe = "".join(ch if ord(ch) < 256 else "?" for ch in str(text))
    return safe.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def block_lines(block: Block) -> list[Line]:
    """Flatten one :class:`Block` into ``(style, text)`` lines."""
    lines: list[Line] = []
    if block.kind == "subheading":
        lines.append(("h3", block.text))
    elif block.kind == "paragraph":
        if block.text.strip():
            lines.append(("para", block.text))
    elif block.kind == "note":
        if block.text.strip():
            lines.append(("note", block.text))
    elif block.kind == "bullets":
        for item in block.items:
            lines.append(("bullet", str(item)))
    elif block.kind == "kv":
        for key, value in block.rows:
            lines.append(("kv", f"{key}: {value}"))
    elif block.kind == "metric":
        for label, value, note in block.metrics:
            suffix = f" — {note}" if note else ""
            lines.append(("metric", f"{label}: {value:.0f}/100{suffix}"))
    return lines


def section_lines(section: Section) -> list[Line]:
    """Flatten a whole section (heading + blocks) into ``(style, text)`` lines."""
    lines: list[Line] = [("h2", f"{section.number}. {section.title}")]
    for block in section.blocks:
        lines.extend(block_lines(block))
    return lines


def document_lines(sections: Iterable[Section]) -> list[Line]:
    """Flatten every section into one ``(style, text)`` line stream."""
    lines: list[Line] = []
    for section in sections:
        lines.extend(section_lines(section))
    return lines
