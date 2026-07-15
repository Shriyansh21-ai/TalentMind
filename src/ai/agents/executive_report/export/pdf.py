"""PDF export — a valid, dependency-free executive PDF.

Reportlab is not a project dependency (and must not become one), so this is a
small, correct PDF 1.4 writer built on the standard library: core Helvetica fonts
(no embedding), word-wrapped text, automatic pagination, a cover page and a
cross-reference table. It renders the same :class:`ReportDocument` IR as every
other exporter, so content never diverges between formats.
"""

from __future__ import annotations

from typing import List, Tuple

from src.ai.agents.executive_report.export._common import pdf_escape
from src.ai.agents.executive_report.renderer import ReportDocument, Section

# US Letter geometry (points).
_PAGE_W, _PAGE_H = 612.0, 792.0
_MARGIN = 56.0
_TOP = 726.0
_BOTTOM = 60.0
_USABLE_W = _PAGE_W - 2 * _MARGIN

# style -> (font_key, size, leading, indent, space_before)
_STYLES = {
    "title": ("Bold", 24, 30, 0, 0),
    "subtitle": ("Regular", 13, 18, 0, 4),
    "cover": ("Regular", 11, 16, 0, 2),
    "h2": ("Bold", 15, 22, 0, 14),
    "h3": ("Bold", 11, 16, 0, 8),
    "para": ("Regular", 10, 14, 0, 4),
    "note": ("Oblique", 9, 13, 0, 4),
    "kv": ("Regular", 10, 14, 8, 2),
    "metric": ("Regular", 10, 14, 8, 2),
    "bullet": ("Regular", 10, 14, 14, 2),
}

_FONT_OBJ = {"Regular": "F1", "Bold": "F2", "Oblique": "F3"}


def _wrap(text: str, size: float, width: float) -> List[str]:
    """Word-wrap ``text`` to ``width`` points at font ``size`` (approx metrics)."""
    max_chars = max(8, int(width / (size * 0.5)))
    words = str(text).split()
    if not words:
        return [""]
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            # Hard-split words longer than a full line.
            while len(word) > max_chars:
                lines.append(word[:max_chars])
                word = word[max_chars:]
            current = word
    if current:
        lines.append(current)
    return lines


def _flatten(document: ReportDocument) -> List[Tuple[str, str]]:
    """Return the full ``(style, text)`` stream including the cover."""
    cover = document.cover
    lines: List[Tuple[str, str]] = [
        ("cover", cover.get("logo", document.brand.product)),
        ("title", document.title),
        ("subtitle", document.subtitle),
        ("cover", f"Recommendation: {cover.get('recommendation', '')}"),
        ("cover", f"Executive Confidence: {cover.get('confidence', '')}"),
        ("cover", f"Audience: {cover.get('audience', '')}"),
        ("cover", f"Candidate: {cover.get('candidate_id', '')}"),
        ("cover", f"Generated: {cover.get('generated_on', '')}"),
        ("h3", "Contents"),
    ]
    for number, title in document.toc:
        lines.append(("kv", f"{number}. {title}"))
    for section in document.sections:
        lines.extend(_section_lines(section))
    return lines


def _section_lines(section: Section) -> List[Tuple[str, str]]:
    from src.ai.agents.executive_report.export._common import section_lines

    return section_lines(section)


def _layout(lines: List[Tuple[str, str]]) -> List[List[Tuple[float, float, str, float, str]]]:
    """Lay lines out into pages. Returns pages of (x, y, font_obj, size, text)."""
    pages: List[List[Tuple[float, float, str, float, str]]] = []
    page: List[Tuple[float, float, str, float, str]] = []
    y = _TOP

    def _new_page() -> None:
        nonlocal page, y
        pages.append(page)
        page = []
        y = _TOP

    for style, text in lines:
        font_key, size, leading, indent, space_before = _STYLES.get(style, _STYLES["para"])
        font_obj = _FONT_OBJ[font_key]
        y -= space_before
        prefix = "- " if style == "bullet" else ""
        wrapped = _wrap(prefix + text if prefix else text, size, _USABLE_W - indent)
        for wline in wrapped:
            if y <= _BOTTOM:
                _new_page()
            page.append((_MARGIN + indent, y, font_obj, size, wline))
            y -= leading
    pages.append(page)
    return pages


def _content_stream(page: List[Tuple[float, float, str, float, str]]) -> bytes:
    """Build a PDF content stream for one laid-out page."""
    parts = ["BT"]
    current_font = None
    current_size = None
    for x, y, font_obj, size, text in page:
        if (font_obj, size) != (current_font, current_size):
            parts.append(f"/{font_obj} {size:.1f} Tf")
            current_font, current_size = font_obj, size
        parts.append(f"1 0 0 1 {x:.1f} {y:.1f} Tm")
        parts.append(f"({pdf_escape(text)}) Tj")
    parts.append("ET")
    return ("\n".join(parts)).encode("latin-1", "replace")


def render(document: ReportDocument) -> bytes:
    """Render the document to a valid PDF byte string."""
    pages = _layout(_flatten(document))

    # Object plan: 1=Catalog, 2=Pages, 3/4/5=Fonts, then page+content pairs.
    objects: List[bytes] = []

    def _add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)  # 1-based object number

    catalog_num = _add(b"<< /Type /Catalog /Pages 2 0 R >>")
    # Placeholder for Pages (object 2); filled after we know kids.
    objects.append(b"")  # reserve slot 2
    pages_num = 2

    f1 = _add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    f2 = _add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    f3 = _add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>")

    resources = (
        f"<< /Font << /F1 {f1} 0 R /F2 {f2} 0 R /F3 {f3} 0 R >> >>"
    ).encode("latin-1")

    page_obj_nums: List[int] = []
    for page in pages:
        stream = _content_stream(page)
        content_num = _add(
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)
        )
        page_dict = (
            f"<< /Type /Page /Parent {pages_num} 0 R "
            f"/MediaBox [0 0 {_PAGE_W:.0f} {_PAGE_H:.0f}] "
            f"/Resources {resources.decode('latin-1')} "
            f"/Contents {content_num} 0 R >>"
        ).encode("latin-1")
        page_obj_nums.append(_add(page_dict))

    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)
    objects[pages_num - 1] = (
        f"<< /Type /Pages /Count {len(page_obj_nums)} /Kids [{kids}] >>"
    ).encode("latin-1")

    # Serialize with a cross-reference table.
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode("latin-1")
        out += obj
        out += b"\nendobj\n"

    xref_pos = len(out)
    count = len(objects) + 1
    out += f"xref\n0 {count}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {count} /Root {catalog_num} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)
