"""HTML export — a self-contained, branded, print-ready executive report.

Produces a single HTML document with inlined CSS (no external assets), so it
opens identically anywhere and can be "printed to PDF" by a browser. Dependency
free; the branding module supplies the enterprise colour + typography system.
"""

from __future__ import annotations

from src.ai.agents.executive_report.export._common import html_escape
from src.ai.agents.executive_report.renderer import Block, ReportDocument, Section


def _css(doc: ReportDocument) -> str:
    b = doc.brand
    return f"""
    :root {{
      --primary: {b.primary}; --secondary: {b.secondary}; --accent: {b.accent};
      --ink: {b.ink}; --muted: {b.muted}; --surface: {b.surface};
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: {b.body_font}; color: var(--ink); margin: 0; background: #fff; line-height: 1.55; }}
    .wrap {{ max-width: 900px; margin: 0 auto; padding: 48px 40px; }}
    h1, h2, h3 {{ font-family: {b.heading_font}; color: var(--primary); }}
    .cover {{ background: linear-gradient(135deg, var(--primary), var(--secondary));
      color: #fff; padding: 64px 40px; border-radius: 0 0 24px 24px; }}
    .cover .logo {{ font-size: 20px; letter-spacing: .5px; opacity: .9; }}
    .cover h1 {{ color: #fff; font-size: 40px; margin: 24px 0 8px; }}
    .cover .sub {{ font-size: 18px; opacity: .92; }}
    .cover .meta {{ margin-top: 28px; display: flex; gap: 32px; flex-wrap: wrap; font-size: 15px; }}
    .cover .meta div span {{ display: block; opacity: .7; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 999px; background: var(--accent);
      color: #fff; font-weight: 600; font-size: 14px; }}
    .toc {{ background: var(--surface); border-radius: 12px; padding: 20px 28px; margin: 32px 0; }}
    .toc h2 {{ margin-top: 0; font-size: 16px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }}
    .toc ol {{ margin: 0; padding-left: 20px; columns: 2; }}
    section.report {{ margin: 40px 0; }}
    section.report > h2 {{ border-bottom: 3px solid var(--accent); padding-bottom: 8px; font-size: 24px; }}
    h3 {{ font-size: 16px; margin: 20px 0 6px; color: var(--secondary); }}
    .kv {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
    .kv td {{ padding: 8px 12px; border-bottom: 1px solid #eef1f5; font-size: 15px; }}
    .kv td.k {{ color: var(--muted); width: 40%; font-weight: 600; }}
    .metric {{ margin: 8px 0; }}
    .metric .label {{ font-size: 14px; color: var(--muted); display: flex; justify-content: space-between; }}
    .bar {{ height: 8px; border-radius: 4px; background: #e7ebf0; overflow: hidden; }}
    .bar > span {{ display: block; height: 100%; background: var(--accent); }}
    ul {{ margin: 6px 0 6px 0; padding-left: 22px; }}
    li {{ margin: 3px 0; }}
    .note {{ color: var(--muted); font-style: italic; font-size: 14px; margin: 10px 0; }}
    footer {{ margin-top: 48px; padding-top: 16px; border-top: 1px solid #e7ebf0;
      color: var(--muted); font-size: 12px; text-align: center; }}
    """


def _render_block(block: Block) -> str:
    if block.kind == "subheading":
        return f"<h3>{html_escape(block.text)}</h3>"
    if block.kind == "paragraph":
        return f"<p>{html_escape(block.text)}</p>" if block.text.strip() else ""
    if block.kind == "note":
        return f"<p class='note'>{html_escape(block.text)}</p>" if block.text.strip() else ""
    if block.kind == "bullets":
        items = "".join(f"<li>{html_escape(i)}</li>" for i in block.items)
        return f"<ul>{items}</ul>"
    if block.kind == "kv":
        rows = "".join(
            f"<tr><td class='k'>{html_escape(k)}</td><td>{html_escape(v)}</td></tr>"
            for k, v in block.rows
        )
        return f"<table class='kv'>{rows}</table>"
    if block.kind == "metric":
        parts: list[str] = []
        for label, value, note in block.metrics:
            pct = max(0.0, min(100.0, float(value)))
            parts.append(
                f"<div class='metric'><div class='label'><span>{html_escape(label)}"
                f"{(' · ' + html_escape(note)) if note else ''}</span><span>{value:.0f}/100</span></div>"
                f"<div class='bar'><span style='width:{pct:.0f}%'></span></div></div>"
            )
        return "".join(parts)
    return ""


def _render_section(section: Section) -> str:
    body = "".join(_render_block(b) for b in section.blocks)
    return f"<section class='report'><h2>{section.number}. {html_escape(section.title)}</h2>{body}</section>"


def render(document: ReportDocument) -> bytes:
    """Render the document to a self-contained HTML byte string."""
    cover = document.cover
    toc = "".join(f"<li>{html_escape(title)}</li>" for _, title in document.toc)
    sections = "".join(_render_section(s) for s in document.sections)
    meta_bits = ""
    for label, key in [
        ("Candidate", "candidate_id"),
        ("Role", "title"),
        ("Audience", "audience"),
        ("Generated", "generated_on"),
    ]:
        value = cover.get(key)
        if value:
            meta_bits += f"<div><span>{html_escape(label)}</span>{html_escape(str(value))}</div>"

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_escape(document.title)} — {html_escape(cover.get("candidate_id", ""))}</title>
<style>{_css(document)}</style></head>
<body>
<div class="cover">
  <div class="logo">{html_escape(cover.get("logo", document.brand.product))}</div>
  <h1>{html_escape(document.title)}</h1>
  <div class="sub">{html_escape(document.subtitle)}</div>
  <div style="margin-top:20px"><span class="badge">{html_escape(cover.get("recommendation", ""))}</span>
    &nbsp;<span class="badge" style="background:rgba(255,255,255,.2)">Confidence: {html_escape(str(cover.get("confidence", "")))}</span></div>
  <div class="meta">{meta_bits}</div>
</div>
<div class="wrap">
  <div class="toc"><h2>Contents</h2><ol>{toc}</ol></div>
  {sections}
  <footer>{html_escape(document.footer)}</footer>
</div>
</body></html>"""
    return html.encode("utf-8")
