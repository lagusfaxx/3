from __future__ import annotations
import re
from typing import List, Dict, Tuple, Optional
from ..settings import settings
from .gateway_client import gateway_chat

REQ_PATTERNS = [
    r"requisit[oa]s?",
    r"obligatori[oa]s?",
    r"deber[aá]n",
    r"debe[n]?",
    r"exig(e|ido|encia)",
    r"garant[ií]a",
    r"multa(s)?",
    r"plazo(s)?",
]

RISK_PATTERNS = [
    r"multa(s)?",
    r"penalidad(es)?",
    r"garant[ií]a",
    r"incumplimiento",
    r"caducidad",
    r"rescisi[oó]n",
    r"responsabilidad",
    r"confidencialidad",
]

def _bullet_extract(text: str, keywords: List[str], limit: int = 12) -> List[str]:
    # Heurística simple: toma líneas que contengan patrones
    lines = [ln.strip() for ln in re.split(r"[\n\r]+", text) if ln.strip()]
    out: List[str] = []
    for ln in lines:
        low = ln.lower()
        if any(re.search(k, low) for k in keywords):
            out.append(ln)
        if len(out) >= limit:
            break
    # Dedup
    seen = set()
    deduped = []
    for item in out:
        k = item.lower()
        if k not in seen:
            seen.add(k)
            deduped.append(item)
    return deduped

def local_analyze(text: str) -> Tuple[str, List[str], List[str], List[str], List[str], str, Dict]:
    # Resumen súper básico
    trimmed = text[:8000]
    summary = (trimmed[:900] + "…") if len(trimmed) > 900 else trimmed

    requirements = _bullet_extract(text, REQ_PATTERNS, limit=12)
    risks = _bullet_extract(text, RISK_PATTERNS, limit=12)

    opportunities = []
    # Ítems requeridos (heurística súper básica)
    required_items = _bullet_extract(text, [r"item", r"ítem", r"cantidad", r"unidad", r"producto"], limit=12)

    # Oportunidades: busca "evaluación", "ponderación", "criterio", "puntaje"
    opportunities = _bullet_extract(text, [r"ponderaci[oó]n", r"criterio(s)?", r"puntaje", r"evaluaci[oó]n"], limit=10)

    proposal = f"""# Propuesta (Borrador)

## Resumen Ejecutivo
{summary if summary else "No se pudo extraer texto suficiente del PDF."}

## Requisitos Clave (detectados)
{chr(10).join([f"- {r}" for r in requirements]) if requirements else "- (No detectados por heurística. Revisa el PDF manualmente.)"}

## Riesgos y Cláusulas Críticas (detectados)
{chr(10).join([f"- {r}" for r in risks]) if risks else "- (No detectados por heurística. Revisa multas, garantías y plazos.)"}

## Oportunidades (criterios / ponderación)
{chr(10).join([f"- {o}" for o in opportunities]) if opportunities else "- (No detectadas por heurística.)"}

## Recomendación
- Preparar carpeta de antecedentes.
- Confirmar plazos, garantías y causales de inadmisibilidad.
- Validar stock y margen antes de ofertar.

"""

    debug = {"mode": "local", "chars": len(text)}
    return summary, requirements, risks, opportunities, required_items, proposal, debug

async def gateway_analyze(
    text: str,
    truth_block: str = "",
    *,
    user_id: str | None = None,
    session_key: str | None = None
) -> Tuple[str, List[str], List[str], List[str], List[str], str, Dict]:

    system = """
Eres el Agente X.

Analizas bases de licitación en español para decidir si conviene participar.

Reglas:
- NO inventes datos
- Si falta información dilo explícitamente
- Usa como fuente de verdad el bloque DATOS VERIFICADOS DEL CLIENTE

Entrega SIEMPRE estas secciones en Markdown:

## Resumen Ejecutivo

## Requisitos Clave

## Riesgos y Cláusulas Críticas

## Oportunidades

## Ítems Requeridos (lo que compra la licitación)

## Recomendación (SI/NO postular + motivo)

## Borrador de Propuesta

En "Ítems Requeridos" usa viñetas con descripción y cantidad si aparece.
"""

    user = f"""{truth_block}

Texto extraído de las bases:

{text[:24000]}
"""

    reply = await gateway_chat(
        user,
        system=system,
        user_id=user_id,
        session_key=session_key
    )

    summary = ""
    requirements: List[str] = []
    risks: List[str] = []
    opportunities: List[str] = []
    proposal = reply

    def section(name: str) -> str:
        pat = rf"(?is)##\s*{name}\s*(.*?)(?=\n##|\Z)"
        m = re.search(pat, reply)
        return m.group(1).strip() if m else ""

    def bullets(block: str, limit: int = 20) -> List[str]:
        items = []
        for ln in block.splitlines():
            ln = ln.strip()
            if ln.startswith("- "):
                items.append(ln[2:])
            if len(items) >= limit:
                break
        return items

    summary_block = section("Resumen Ejecutivo")

    if summary_block:
        summary = summary_block[:600]

    requirements = bullets(section("Requisitos Clave"))
    risks = bullets(section("Riesgos y Cláusulas Críticas"))
    opportunities = bullets(section("Oportunidades"))
    required_items = bullets(section("Ítems Requeridos"), limit=30)

    debug = {
        "mode": "gateway",
        "gateway_url": str(settings.gateway_url)
    }

    return summary, requirements, risks, opportunities, required_items, proposal, debug