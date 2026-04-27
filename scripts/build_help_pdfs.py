"""Convert Asset Pulse help markdown into branded PDFs.

Each output PDF carries an "Asset Pulse" header on every page with the Pulse
Drop logo (drawn as vector art so we don't depend on a rasterizer). Citation-
style URLs in the source Markdown are extracted and rendered as clickable
links. Run from repo root:

    python3 scripts/build_help_pdfs.py
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
OUT_DIR = DOCS_DIR / "pdf"

BRAND_ORANGE = colors.HexColor("#c2530b")
BRAND_DARK = colors.HexColor("#2b1d0e")
BRAND_MUTED = colors.HexColor("#6b553a")

# Source markdown -> output PDF + pretty title
DOC_MAP: list[tuple[str, str, str]] = [
    ("application-help.pplx.md", "application-help.pdf", "Asset Pulse Application Help"),
    ("help-me-calculation-guide.pplx.md", "help-me-calculation-guide.pdf",
     "Help Me Calculation Guide — CAPEX / OPEX / Fiscal Inputs"),
    ("docker-desktop-deployment.pplx.md", "docker-desktop-deployment.pdf",
     "Docker Desktop Deployment Guide"),
    ("windows-executable-distribution.pplx.md", "windows-executable-distribution.pdf",
     "Windows Executable Distribution"),
    ("middle-east-capex-opex-fiscal-methodology.pplx.md",
     "middle-east-capex-opex-fiscal-methodology.pdf",
     "Middle East CAPEX / OPEX & Fiscal Methodology"),
    ("oil-well-capex-opex-knowledge-base.pplx.md",
     "oil-well-capex-opex-knowledge-base.pdf",
     "Oil Well CAPEX / OPEX Knowledge Base"),
    ("local-deployment-postgresql17.pplx.md", "local-deployment-postgresql17.pdf",
     "Local Deployment — PostgreSQL 17"),
]


def _draw_logo(c: Canvas, x: float, y: float, size: float = 16.0) -> None:
    """Draw a compact Pulse Drop mark (oil droplet + pulse line) as vector art.

    Coordinates use the bottom-left origin convention of ReportLab. ``size``
    is the bounding-box height in points.
    """
    s = size / 64.0  # the SVG was authored in a 64-unit viewBox

    def X(u: float) -> float:
        return x + u * s

    def Y(u: float) -> float:
        return y + (64 - u) * s

    # Droplet outline: M 32 6 C 22 22, 14 30, 14 40 A 18 18 0 0 0 50 40 C 50 30, 42 22, 32 6 Z
    p = c.beginPath()
    p.moveTo(X(32), Y(6))
    p.curveTo(X(22), Y(22), X(14), Y(30), X(14), Y(40))
    # Approximate the bottom semicircle with a single curve — close enough at
    # this size to read as a droplet.
    p.curveTo(X(14), Y(54), X(50), Y(54), X(50), Y(40))
    p.curveTo(X(50), Y(30), X(42), Y(22), X(32), Y(6))
    p.close()
    c.setStrokeColor(BRAND_DARK)
    c.setLineWidth(1.6 * s)
    c.drawPath(p, stroke=1, fill=0)

    # Pulse line: H 18 41 to 46 30
    pulse_pts = [
        (18, 41), (24, 41), (26.5, 35), (29, 47), (31.5, 33),
        (34, 43), (37, 41), (41, 36), (46, 30),
    ]
    c.setStrokeColor(BRAND_DARK)
    c.setLineWidth(1.2 * s)
    p2 = c.beginPath()
    p2.moveTo(X(pulse_pts[0][0]), Y(pulse_pts[0][1]))
    for ux, uy in pulse_pts[1:]:
        p2.lineTo(X(ux), Y(uy))
    c.drawPath(p2, stroke=1, fill=0)

    # Brand-orange endpoint dot + outbound stroke
    c.setFillColor(BRAND_ORANGE)
    c.setStrokeColor(BRAND_ORANGE)
    c.circle(X(46), Y(30), 1.8 * s, stroke=0, fill=1)
    c.setLineWidth(1.2 * s)
    c.line(X(46), Y(30), X(50), Y(26))


def _make_header_footer(title: str):
    def _draw(canvas: Canvas, doc) -> None:
        canvas.saveState()
        page_w, page_h = LETTER
        # Top header band — kept light so it survives B/W printing.
        canvas.setFillColor(colors.HexColor("#f1e7d3"))
        canvas.rect(0, page_h - 0.55 * inch, page_w, 0.55 * inch, fill=1, stroke=0)
        # Bottom orange rule
        canvas.setStrokeColor(BRAND_ORANGE)
        canvas.setLineWidth(0.8)
        canvas.line(0.6 * inch, page_h - 0.55 * inch, page_w - 0.6 * inch,
                    page_h - 0.55 * inch)

        # Logo + wordmark
        logo_x = 0.6 * inch
        logo_y = page_h - 0.5 * inch
        _draw_logo(canvas, logo_x, logo_y, size=22)

        canvas.setFillColor(BRAND_ORANGE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(logo_x + 30, page_h - 0.32 * inch, "ASSET PULSE")
        canvas.setFillColor(BRAND_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(logo_x + 30, page_h - 0.45 * inch,
                          "Forecasting & Decision Intelligence")

        # Right-aligned section title
        canvas.setFillColor(BRAND_DARK)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawRightString(page_w - 0.6 * inch, page_h - 0.32 * inch, title)
        canvas.setFillColor(BRAND_MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(page_w - 0.6 * inch, page_h - 0.45 * inch,
                               f"Page {doc.page}")

        # Footer
        canvas.setFillColor(BRAND_MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(0.6 * inch, 0.4 * inch,
                          "Asset Pulse — generated help reference")
        canvas.drawRightString(page_w - 0.6 * inch, 0.4 * inch,
                               "© Perplexity Computer")
        canvas.restoreState()

    return _draw


def _make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "ApBody", parent=base["BodyText"], fontName="Helvetica",
        fontSize=10, leading=14, textColor=BRAND_DARK, alignment=TA_LEFT,
        spaceAfter=4,
    )
    h1 = ParagraphStyle(
        "ApH1", parent=base["Heading1"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=BRAND_ORANGE,
        spaceBefore=10, spaceAfter=8,
    )
    h2 = ParagraphStyle(
        "ApH2", parent=base["Heading2"], fontName="Helvetica-Bold",
        fontSize=14, leading=18, textColor=BRAND_ORANGE,
        spaceBefore=10, spaceAfter=6,
    )
    h3 = ParagraphStyle(
        "ApH3", parent=base["Heading3"], fontName="Helvetica-Bold",
        fontSize=11.5, leading=15, textColor=BRAND_DARK,
        spaceBefore=8, spaceAfter=4,
    )
    bullet = ParagraphStyle(
        "ApBullet", parent=body, leftIndent=14, bulletIndent=4,
        spaceAfter=2,
    )
    code = ParagraphStyle(
        "ApCode", parent=body, fontName="Courier", fontSize=8.5, leading=11,
        textColor=BRAND_DARK, backColor=colors.HexColor("#f6ecd6"),
        borderPadding=4,
    )
    return {"body": body, "h1": h1, "h2": h2, "h3": h3, "bullet": bullet, "code": code}


_INLINE_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_BARE_URL = re.compile(r"(?<!\()(?<!\[)(https?://[^\s)\]]+)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_EMPH = re.compile(r"(?<![*_])\*([^*]+)\*(?!\*)")
_INLINE_CODE = re.compile(r"`([^`]+)`")


def _md_inline(text: str) -> str:
    """Translate a single line of inline Markdown into ReportLab paragraph XML.

    Pulls links/code out into placeholder tokens BEFORE XML escaping so URLs
    aren't double-rewritten and ampersands inside hrefs are handled cleanly.
    """
    placeholders: list[str] = []

    def _stash(html: str) -> str:
        placeholders.append(html)
        return f"\x00{len(placeholders) - 1}\x00"

    def _link_repl(m: re.Match[str]) -> str:
        label = (
            m.group(1).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;")
        )
        href = m.group(2).replace("&", "&amp;")
        return _stash(f'<link href="{href}" color="#c2530b">{label}</link>')

    def _bare_repl(m: re.Match[str]) -> str:
        url = m.group(1)
        href = url.replace("&", "&amp;")
        return _stash(f'<link href="{href}" color="#c2530b">{url}</link>')

    def _code_repl(m: re.Match[str]) -> str:
        body = (
            m.group(1).replace("&", "&amp;")
            .replace("<", "&lt;").replace(">", "&gt;")
        )
        return _stash(f'<font name="Courier" size="9">{body}</font>')

    out = _INLINE_LINK.sub(_link_repl, text)
    out = _BARE_URL.sub(_bare_repl, out)
    out = _INLINE_CODE.sub(_code_repl, out)

    # Now escape any remaining XML metacharacters in the plain text
    out = (
        out.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    out = _BOLD.sub(r"<b>\1</b>", out)
    out = _EMPH.sub(r"<i>\1</i>", out)

    # Restore placeholders
    def _restore(m: re.Match[str]) -> str:
        return placeholders[int(m.group(1))]

    out = re.sub(r"\x00(\d+)\x00", _restore, out)
    return out


def _table_from_md(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    body = styles["body"]
    data = [[Paragraph(_md_inline(cell), body) for cell in row] for row in rows]
    n_cols = max(len(r) for r in data)
    # Equal-width columns, total ~6.8 inches
    col_w = 6.8 * inch / n_cols
    t = Table(data, colWidths=[col_w] * n_cols, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede0c5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_DARK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, BRAND_ORANGE),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d6bf94")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _md_to_flowables(md: str, styles: dict[str, ParagraphStyle]) -> list:
    """Light-weight Markdown to ReportLab flowables.

    Handles: headings (#, ##, ###), bullet lists (-, *), numbered lists,
    fenced code blocks (```), GitHub-flavored pipe tables, paragraphs, and
    inline emphasis/links.
    """
    lines = md.splitlines()
    out: list = []
    i = 0
    n = len(lines)
    body = styles["body"]

    def flush_para(buf: list[str]) -> None:
        if not buf:
            return
        text = " ".join(s.strip() for s in buf if s.strip())
        if text:
            out.append(Paragraph(_md_inline(text), body))
        buf.clear()

    para_buf: list[str] = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            flush_para(para_buf)
            i += 1
            code_lines: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            out.append(Preformatted("\n".join(code_lines), styles["code"]))
            out.append(Spacer(1, 4))
            continue

        # Headings
        if stripped.startswith("### "):
            flush_para(para_buf)
            out.append(Paragraph(_md_inline(stripped[4:]), styles["h3"]))
            i += 1
            continue
        if stripped.startswith("## "):
            flush_para(para_buf)
            out.append(Paragraph(_md_inline(stripped[3:]), styles["h2"]))
            i += 1
            continue
        if stripped.startswith("# "):
            flush_para(para_buf)
            out.append(Paragraph(_md_inline(stripped[2:]), styles["h1"]))
            i += 1
            continue

        # Pipe table (must have a separator row of |---|---|)
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            flush_para(para_buf)
            tbl_rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                tbl_rows.append(row)
                i += 1
            # Drop the separator line (the second row of dashes)
            tbl_rows = [r for r in tbl_rows if not all(re.match(r"^:?-{2,}:?$", c) for c in r if c)]
            if tbl_rows:
                out.append(_table_from_md(tbl_rows, styles))
                out.append(Spacer(1, 6))
            continue

        # Bullet list
        m = re.match(r"^[-*]\s+(.*)", stripped)
        if m:
            flush_para(para_buf)
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                out.append(Paragraph("• " + _md_inline(item), styles["bullet"]))
                i += 1
            out.append(Spacer(1, 2))
            continue

        # Numbered list
        m = re.match(r"^(\d+)\.\s+(.*)", stripped)
        if m:
            flush_para(para_buf)
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                m2 = re.match(r"^(\d+)\.\s+(.*)", lines[i].strip())
                if not m2:
                    break
                out.append(Paragraph(f"{m2.group(1)}. " + _md_inline(m2.group(2)),
                                      styles["bullet"]))
                i += 1
            out.append(Spacer(1, 2))
            continue

        # Blank line — paragraph break
        if not stripped:
            flush_para(para_buf)
            i += 1
            continue

        # Default: accumulate paragraph text
        para_buf.append(line)
        i += 1

    flush_para(para_buf)
    return out


def build_pdf(md_path: Path, out_path: Path, title: str) -> None:
    md = md_path.read_text(encoding="utf-8")
    styles = _make_styles()
    flowables = _md_to_flowables(md, styles)

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.65 * inch,
        title=title,
        author="Perplexity Computer",
        subject="Asset Pulse help reference",
        creator="Asset Pulse build_help_pdfs.py",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="content",
    )
    template = PageTemplate(id="ap", frames=[frame],
                            onPage=_make_header_footer(title))
    doc.addPageTemplates([template])
    doc.build(flowables)


def build_all() -> Iterable[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built: list[Path] = []
    for src_name, out_name, title in DOC_MAP:
        src = DOCS_DIR / src_name
        if not src.exists():
            print(f"  skip {src_name} (not found)")
            continue
        out = OUT_DIR / out_name
        build_pdf(src, out, title)
        print(f"  built {out.relative_to(REPO_ROOT)}")
        built.append(out)
    return built


if __name__ == "__main__":
    print(f"Building Asset Pulse help PDFs into {OUT_DIR.relative_to(REPO_ROOT)}")
    built = list(build_all())
    print(f"Done. {len(built)} PDF(s) generated.")
