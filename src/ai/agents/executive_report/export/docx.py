"""DOCX export — a valid Word document, dependency-free.

python-docx is not a project dependency, so this writes minimal-but-valid
WordprocessingML (OOXML) directly into a zip with the standard library. It renders
the shared :class:`ReportDocument` IR with direct run formatting (bold headings,
sized text, bullets), so the Word output matches the HTML/PDF/PPTX exactly.
"""

from __future__ import annotations

import io
import zipfile
from typing import List, Tuple

from src.ai.agents.executive_report.export._common import section_lines, xml_escape
from src.ai.agents.executive_report.renderer import ReportDocument, Section

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>"""

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# style -> (half_point_size, bold, italic, color_hex, bullet)
_STYLES = {
    "title": (48, True, False, "0B1F3A", False),
    "subtitle": (26, False, True, "5B6B7B", False),
    "cover": (22, False, False, "1A1A2E", False),
    "h2": (30, True, False, "0B1F3A", False),
    "h3": (24, True, False, "13315C", False),
    "para": (21, False, False, "1A1A2E", False),
    "note": (18, False, True, "5B6B7B", False),
    "kv": (21, False, False, "1A1A2E", False),
    "metric": (21, False, False, "1A1A2E", False),
    "bullet": (21, False, False, "1A1A2E", True),
}


def _paragraph(style: str, text: str) -> str:
    size, bold, italic, color, bullet = _STYLES.get(style, _STYLES["para"])
    ppr = ['<w:spacing w:before="80" w:after="40"/>']
    if bullet:
        ppr.append('<w:ind w:left="360" w:hanging="180"/>')
    rpr = [f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>', f'<w:color w:val="{color}"/>']
    if bold:
        rpr.append("<w:b/>")
    if italic:
        rpr.append("<w:i/>")
    prefix = "• " if bullet else ""
    return (
        "<w:p><w:pPr>" + "".join(ppr) + "</w:pPr>"
        "<w:r><w:rPr>" + "".join(rpr) + "</w:rPr>"
        f'<w:t xml:space="preserve">{xml_escape(prefix + text)}</w:t></w:r></w:p>'
    )


def _cover_lines(document: ReportDocument) -> List[Tuple[str, str]]:
    cover = document.cover
    return [
        ("cover", cover.get("logo", document.brand.product)),
        ("title", document.title),
        ("subtitle", document.subtitle),
        ("cover", f"Recommendation: {cover.get('recommendation', '')}"),
        ("cover", f"Executive Confidence: {cover.get('confidence', '')}"),
        ("cover", f"Audience: {cover.get('audience', '')}"),
        ("cover", f"Candidate: {cover.get('candidate_id', '')}"),
        ("cover", f"Generated: {cover.get('generated_on', '')}"),
        ("h3", "Contents"),
        *[("kv", f"{n}. {t}") for n, t in document.toc],
    ]


def _document_xml(document: ReportDocument) -> str:
    lines: List[Tuple[str, str]] = _cover_lines(document)
    for section in document.sections:
        lines.extend(section_lines(section))
    lines.append(("note", document.footer))
    body = "".join(_paragraph(style, text) for style, text in lines)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W}"><w:body>{body}'
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>'
        "</w:body></w:document>"
    )


def render(document: ReportDocument) -> bytes:
    """Render the document to a valid .docx byte string."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", _document_xml(document))
        zf.writestr("word/_rels/document.xml.rels", _DOC_RELS)
    return buffer.getvalue()
