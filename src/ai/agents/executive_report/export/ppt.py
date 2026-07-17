"""PPTX export — a valid PowerPoint deck, dependency-free.

python-pptx is not a project dependency, so this writes minimal-but-valid
PresentationML (OOXML) directly into a zip with the standard library: the full
required part chain (presentation → slide master → layout → theme → slides), a
title slide from the cover, and one content slide per report section. Same
:class:`ReportDocument` IR as the other exporters.
"""

from __future__ import annotations

import io
import zipfile

from src.ai.agents.executive_report.export._common import section_lines, xml_escape
from src.ai.agents.executive_report.renderer import ReportDocument

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_EMU_W, _EMU_H = 9144000, 6858000  # 10 x 7.5 inches


def _theme() -> str:
    # A minimal but complete theme (colour scheme + font scheme + format scheme).
    dk = "0B1F3A"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{_A}" name="TalentMind">
<a:themeElements>
<a:clrScheme name="TalentMind">
<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="{dk}"/></a:dk2><a:lt2><a:srgbClr val="F5F7FA"/></a:lt2>
<a:accent1><a:srgbClr val="2E86DE"/></a:accent1><a:accent2><a:srgbClr val="13315C"/></a:accent2>
<a:accent3><a:srgbClr val="1E8449"/></a:accent3><a:accent4><a:srgbClr val="E67E22"/></a:accent4>
<a:accent5><a:srgbClr val="8E44AD"/></a:accent5><a:accent6><a:srgbClr val="C0392B"/></a:accent6>
<a:hlink><a:srgbClr val="2E86DE"/></a:hlink><a:folHlink><a:srgbClr val="8E44AD"/></a:folHlink>
</a:clrScheme>
<a:fontScheme name="TalentMind">
<a:majorFont><a:latin typeface="Georgia"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Segoe UI"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
</a:fontScheme>
<a:fmtScheme name="TalentMind">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme>
</a:themeElements></a:theme>"""


def _slide_master() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}">
<p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="lt1"/></p:bgRef></p:bg>
<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
<p:txStyles>
<p:titleStyle><a:lvl1pPr><a:defRPr sz="3200"><a:solidFill><a:schemeClr val="dk2"/></a:solidFill></a:defRPr></a:lvl1pPr></p:titleStyle>
<p:bodyStyle><a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>
<p:otherStyle/></p:txStyles></p:sldMaster>"""


def _slide_layout() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}" type="blank" preserve="1">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1"
accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sldLayout>"""


def _textbox(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, paragraphs: str) -> str:
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{name}"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>{paragraphs}</p:txBody></p:sp>'
    )


def _para(text: str, size: int, bold: bool, color: str) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:p><a:r><a:rPr lang="en-US" sz="{size}"{b}>'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill></a:rPr>'
        f"<a:t>{xml_escape(text)}</a:t></a:r></a:p>"
    )


def _slide_xml(title: str, lines: list[tuple[str, str]], *, is_cover: bool = False) -> str:
    title_para = _para(title, 3200 if is_cover else 2400, True, "0B1F3A")
    body_paras: list[str] = []
    for style, text in lines:
        if style == "h3":
            body_paras.append(_para(text, 1600, True, "13315C"))
        elif style in ("note",):
            body_paras.append(_para(text, 1200, False, "5B6B7B"))
        elif style == "bullet":
            body_paras.append(_para("• " + text, 1400, False, "1A1A2E"))
        else:
            body_paras.append(_para(text, 1400, False, "1A1A2E"))
    title_box = _textbox(2, "Title", 457200, 274638, 8229600, 1143000, title_para)
    body_box = _textbox(
        3,
        "Body",
        457200,
        1600200,
        8229600,
        4800600,
        "".join(body_paras) or _para("", 1400, False, "1A1A2E"),
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        f"{title_box}{body_box}"
        '</p:spTree></p:cSld><p:clrMapOvr><a:overrideClrMapping bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2"'
        ' accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5"'
        ' accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr></p:sld>'
    )


def _build_slides(document: ReportDocument) -> list[str]:
    cover = document.cover
    slides: list[str] = []
    cover_lines: list[tuple[str, str]] = [
        ("h3", document.subtitle),
        ("para", f"Recommendation: {cover.get('recommendation', '')}"),
        ("para", f"Executive Confidence: {cover.get('confidence', '')}"),
        ("para", f"Audience: {cover.get('audience', '')}"),
        ("para", f"Candidate: {cover.get('candidate_id', '')}"),
        ("note", f"Generated: {cover.get('generated_on', '')}"),
    ]
    slides.append(_slide_xml(document.title, cover_lines, is_cover=True))
    for section in document.sections:
        lines = section_lines(section)
        # First line is the section heading (h2); use it as the slide title.
        heading = lines[0][1] if lines else section.title
        slides.append(_slide_xml(heading, lines[1:]))
    return slides


def _presentation_xml(n_slides: int) -> str:
    ids = "".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 2}"/>' for i in range(n_slides))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:a="{_A}" xmlns:r="{_R}" xmlns:p="{_P}">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f"<p:sldIdLst>{ids}</p:sldIdLst>"
        f'<p:sldSz cx="{_EMU_W}" cy="{_EMU_H}"/><p:notesSz cx="{_EMU_H}" cy="{_EMU_W}"/>'
        "</p:presentation>"
    )


def render(document: ReportDocument) -> bytes:
    """Render the document to a valid .pptx byte string."""
    slides = _build_slides(document)
    n = len(slides)

    # Content types.
    slide_overrides = "".join(
        f'<Override PartName="/ppt/slides/slide{i + 1}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(n)
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        f"{slide_overrides}</Types>"
    )

    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{_R}/officeDocument" Target="ppt/presentation.xml"/>'
        "</Relationships>"
    )

    # presentation rels: master + one per slide.
    pres_rel_items = [
        f'<Relationship Id="rId1" Type="{_R}/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    ]
    for i in range(n):
        pres_rel_items.append(
            f'<Relationship Id="rId{i + 2}" Type="{_R}/slide" Target="slides/slide{i + 1}.xml"/>'
        )
    pres_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(pres_rel_items)
        + "</Relationships>"
    )

    master_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{_R}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
        f'<Relationship Id="rId2" Type="{_R}/theme" Target="../theme/theme1.xml"/>'
        "</Relationships>"
    )
    layout_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{_R}/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
        "</Relationships>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", _presentation_xml(n))
        zf.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        zf.writestr("ppt/slideMasters/slideMaster1.xml", _slide_master())
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", _slide_layout())
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        zf.writestr("ppt/theme/theme1.xml", _theme())
        for i, slide in enumerate(slides):
            zf.writestr(f"ppt/slides/slide{i + 1}.xml", slide)
            zf.writestr(
                f"ppt/slides/_rels/slide{i + 1}.xml.rels",
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="{_R}/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                "</Relationships>",
            )
    return buffer.getvalue()
