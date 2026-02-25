from __future__ import annotations

from io import BytesIO
from typing import List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, max_width: float, leading: float = 14) -> float:
    """Draw wrapped text and return new y position."""
    if not text:
        return y
    # crude wrap by character count approximation
    # 1 char ~ 6 pts at 11-12pt fonts (rough)
    chars_per_line = max(20, int(max_width / 6))
    lines: List[str] = []
    for paragraph in str(text).splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        buf = paragraph
        while len(buf) > chars_per_line:
            cut = buf.rfind(" ", 0, chars_per_line)
            if cut == -1:
                cut = chars_per_line
            lines.append(buf[:cut].rstrip())
            buf = buf[cut:].lstrip()
        lines.append(buf)

    for line in lines:
        if y < 1 * inch:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = 10.5 * inch
        c.drawString(x, y, line)
        y -= leading
    return y


def build_report_pdf(
    *,
    title: str,
    filename: str,
    summary: str,
    requirements: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    opportunities: Optional[List[str]] = None,
    required_items: Optional[List[str]] = None,
    inventory_matches: Optional[List[dict]] = None,
    proposal_markdown: str = "",
) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    # Header
    c.setTitle(title)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, h - 1 * inch, title)

    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, h - 1.25 * inch, f"Archivo: {filename}")

    y = h - 1.7 * inch

    def section(name: str):
        nonlocal y
        if y < 1.5 * inch:
            c.showPage()
            y = h - 1 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y, name)
        y -= 0.3 * inch
        c.setFont("Helvetica", 11)

    # Summary
    section("Resumen ejecutivo")
    y = _draw_wrapped(c, summary, 1 * inch, y, w - 2 * inch)

    # Lists
    def bullet_list(items: Optional[List[str]]):
        nonlocal y
        items = items or []
        if not items:
            y = _draw_wrapped(c, "(vacío)", 1 * inch, y, w - 2 * inch)
            return
        for it in items:
            if y < 1 * inch:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = h - 1 * inch
            c.drawString(1 * inch, y, u"• " + str(it))
            y -= 14

    section("Requisitos clave")
    bullet_list(requirements)

    section("Riesgos / alertas")
    bullet_list(risks)

    section("Oportunidades")
    bullet_list(opportunities)

    
    section("Ítems requeridos")
    bullet_list(required_items)

    section("Cruce con inventario (mejor match)")
    invm = inventory_matches or []
    if not invm:
        y = _draw_wrapped(c, "(sin cruces; inventario vacío o no se detectaron ítems)", 1 * inch, y, w - 2 * inch)
    else:
        for row in invm[:30]:
            if y < 1 * inch:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = h - 1 * inch
            req = str(row.get("required",""))
            matches = row.get("matches") or []
            best = matches[0] if matches else None
            if best:
                line = f"• {req}  →  {best.get('name')} (score {best.get('score')}) | costo {best.get('cost')} | stock {best.get('stock')}"
            else:
                line = f"• {req}  →  (sin match en inventario)"
            y = _draw_wrapped(c, line, 1 * inch, y, w - 2 * inch, leading=13)

    section("Borrador de propuesta (texto)")
    # Strip markdown a bit (keep readable)
    md = proposal_markdown or ""
    md = md.replace("**", "").replace("## ", "").replace("# ", "")
    y = _draw_wrapped(c, md, 1 * inch, y, w - 2 * inch, leading=13)

    c.showPage()
    c.save()
    return buf.getvalue()
