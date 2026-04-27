"""PDF report generation for scenario comparison.

Builds a multi-page PDF using ReportLab Platypus from a list of saved scenarios
returned by /api/scenarios. Designed to be called from /api/scenarios/report.pdf.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


def _fmt_usd(v: float | int | None) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if f < 0 else ""
    return f"{sign}${abs(f):,.0f}"


def _fmt_num(v: float | int | None, digits: int = 2) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _interpret(scenarios: list[dict]) -> list[str]:
    """Short, data-driven interpretation bullets for the cover page."""
    if not scenarios:
        return ["No scenarios available for comparison."]
    with_npv = [s for s in scenarios if (s.get("result") or {}).get("npv") is not None]
    notes: list[str] = []
    if with_npv:
        best = max(with_npv, key=lambda s: s["result"]["npv"])
        worst = min(with_npv, key=lambda s: s["result"]["npv"])
        notes.append(
            f"Highest NPV: <b>{best['name']}</b> at {_fmt_usd(best['result']['npv'])}."
        )
        if best["id"] != worst["id"]:
            notes.append(
                f"Lowest NPV: <b>{worst['name']}</b> at {_fmt_usd(worst['result']['npv'])}."
            )
    with_be = [
        s for s in scenarios
        if (s.get("result") or {}).get("breakeven_oil_price") is not None
    ]
    if with_be:
        cheapest = min(with_be, key=lambda s: s["result"]["breakeven_oil_price"])
        notes.append(
            f"Most resilient breakeven oil: <b>{cheapest['name']}</b> at "
            f"${cheapest['result']['breakeven_oil_price']:.2f}/bbl."
        )
    with_pb = [
        s for s in scenarios
        if (s.get("result") or {}).get("payback_months") is not None
    ]
    if with_pb:
        fastest = min(with_pb, key=lambda s: s["result"]["payback_months"])
        notes.append(
            f"Fastest payback: <b>{fastest['name']}</b> at "
            f"{fastest['result']['payback_months']:.1f} months."
        )
    notes.append(
        "NPV / PV-10 use the discount rate stored on each scenario; "
        "breakeven oil is the price that drives NPV to ~zero with all other inputs held."
    )
    return notes


def _bar_table(rows: list[tuple[str, float | None, str]], *, signed: bool) -> Table:
    """Tiny ASCII-style bar chart drawn as a table for portability without
    matplotlib. ``rows`` is (label, value, display_str)."""
    if not rows:
        return Table([["(no data)"]])
    max_abs = max((abs(v) for _, v, _ in rows if v is not None), default=1.0) or 1.0
    bar_width = 28  # characters
    table_data: list[list[Any]] = [["Scenario", "Bar", "Value"]]
    for label, value, display in rows:
        if value is None:
            bar = ""
        elif signed:
            half = bar_width // 2
            n = int(round(abs(value) / max_abs * half))
            if value >= 0:
                bar = (" " * half) + ("█" * n) + (" " * (half - n))
            else:
                bar = (" " * (half - n)) + ("█" * n) + (" " * half)
        else:
            n = int(round(abs(value) / max_abs * bar_width))
            bar = ("█" * n) + (" " * (bar_width - n))
        table_data.append([label, bar, display])
    t = Table(table_data, colWidths=[2.4 * inch, 2.6 * inch, 1.4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (1, 1), (1, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def build_scenario_comparison_pdf(scenarios: Iterable[dict]) -> bytes:
    items = list(scenarios)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title="Asset Pulse Scenario Comparison Report",
        author="Asset Pulse",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=18, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, spaceAfter=6, spaceBefore=10)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=13)
    muted = ParagraphStyle("muted", parent=body, textColor=colors.HexColor("#555"))

    story: list[Any] = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph("Asset Pulse Scenario Comparison Report", h1))
    story.append(Paragraph(f"Generated: {ts}", muted))
    story.append(Paragraph(f"Scenarios compared: {len(items)}", muted))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Interpretation", h2))
    for note in _interpret(items):
        story.append(Paragraph("• " + note, body))

    story.append(Paragraph("Comparison table", h2))
    head = [
        "ID", "Scenario", "Asset", "Regime",
        "NPV", "PV-10", "Payback (mo)", "Breakeven $/bbl",
    ]
    rows: list[list[Any]] = [head]
    for it in items:
        r = it.get("result") or {}
        rows.append([
            str(it.get("id", "—")),
            Paragraph(str(it.get("name") or "—"), body),
            Paragraph(str(it.get("asset_alias") or "—"), body),
            r.get("fiscal_regime") or it.get("inputs", {}).get("fiscal_regime") or "—",
            _fmt_usd(r.get("npv")),
            _fmt_usd(r.get("pv10")),
            _fmt_num(r.get("payback_months"), 1),
            _fmt_num(r.get("breakeven_oil_price"), 2),
        ])
    table = Table(rows, repeatRows=1, colWidths=[
        0.45 * inch, 1.5 * inch, 1.2 * inch, 0.95 * inch,
        0.9 * inch, 0.9 * inch, 0.7 * inch, 0.85 * inch,
    ])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
    ]))
    story.append(table)

    npv_rows = [
        (it.get("name") or f"#{it.get('id')}", (it.get("result") or {}).get("npv"),
         _fmt_usd((it.get("result") or {}).get("npv")))
        for it in items
    ]
    story.append(Paragraph("NPV comparison (signed bars)", h2))
    story.append(_bar_table(npv_rows, signed=True))

    be_rows = [
        (it.get("name") or f"#{it.get('id')}",
         (it.get("result") or {}).get("breakeven_oil_price"),
         _fmt_num((it.get("result") or {}).get("breakeven_oil_price"), 2) + " $/bbl")
        for it in items
    ]
    story.append(Spacer(1, 6))
    story.append(Paragraph("Breakeven oil price (lower = more resilient)", h2))
    story.append(_bar_table(be_rows, signed=False))

    if any((it.get("result") or {}).get("payback_months") is not None for it in items):
        pb_rows = [
            (it.get("name") or f"#{it.get('id')}",
             (it.get("result") or {}).get("payback_months"),
             _fmt_num((it.get("result") or {}).get("payback_months"), 1) + " mo")
            for it in items
        ]
        story.append(Spacer(1, 6))
        story.append(Paragraph("Payback months (lower = faster)", h2))
        story.append(_bar_table(pb_rows, signed=False))

    story.append(PageBreak())
    story.append(Paragraph("Per-scenario details", h1))
    for it in items:
        r = it.get("result") or {}
        inp = it.get("inputs") or {}
        story.append(Paragraph(f"#{it.get('id')} · {it.get('name') or '—'}", h2))
        story.append(Paragraph(
            f"Asset alias: <b>{it.get('asset_alias') or '—'}</b> · Source: "
            f"<b>{it.get('source') or '—'}</b> · Regime: <b>"
            f"{r.get('fiscal_regime') or inp.get('fiscal_regime') or '—'}</b>",
            body,
        ))
        kpi_rows = [
            ["NPV", _fmt_usd(r.get("npv"))],
            ["PV-10", _fmt_usd(r.get("pv10"))],
            ["Payback (months)", _fmt_num(r.get("payback_months"), 1)],
            ["Breakeven oil ($/bbl)", _fmt_num(r.get("breakeven_oil_price"), 2)],
            ["Netback ($/BOE)", _fmt_num(r.get("netback_per_boe"), 2)],
            ["Total BOE", _fmt_num(r.get("total_boe"), 0)],
        ]
        kpi_table = Table(kpi_rows, colWidths=[2.2 * inch, 2.2 * inch])
        kpi_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbb")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 6))
        key_inputs = [
            ("Horizon (mo)", inp.get("months_horizon")),
            ("Initial oil (bopd)", inp.get("initial_oil_bopd")),
            ("Annual decline", inp.get("annual_decline")),
            ("Oil price ($/bbl)", inp.get("oil_price")),
            ("Dev CAPEX ($)", inp.get("development_capex")),
            ("Discount rate", inp.get("discount_rate_annual")),
        ]
        ki_rows = [["Input", "Value"]] + [[k, _fmt_num(v, 4) if v is not None else "—"] for k, v in key_inputs]
        ki_table = Table(ki_rows, colWidths=[2.2 * inch, 2.2 * inch])
        ki_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#bbb")),
        ]))
        story.append(ki_table)
        story.append(Spacer(1, 12))

    story.append(Paragraph(
        "Generated by Asset Pulse from saved scenario data. NPV and PV-10 reflect "
        "the discount rate stored with each scenario; breakeven is the oil price "
        "that drives NPV to zero. This report does not include external citations.",
        muted,
    ))

    doc.build(story)
    return buf.getvalue()


__all__ = ["build_scenario_comparison_pdf"]
