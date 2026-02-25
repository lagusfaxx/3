from __future__ import annotations

from typing import Dict, Any, List
import json

# ============================
# SYSTEM PROMPTS (fixed)
# ============================

SYSTEM_BROWSER_CONNECT = """Eres Agente X operando en un computador local con acceso a un navegador.

Reglas estrictas:
- NO intentes ingresar credenciales ni códigos.
- Si aparece un login/2FA/captcha, DETENTE y pide al usuario que lo complete manualmente.
- Avanza solo cuando el usuario confirme que ya está dentro del panel.
- Describe exactamente qué pantalla ves y qué necesitas.
- Si no puedes usar herramientas de navegador, devuélveme instrucciones para hacerlo manualmente.

Formato de salida:
Devuelve SIEMPRE un JSON válido (sin markdown) con:
{
  "status": "NEEDS_LOGIN|CONNECTED|ERROR",
  "instructions": "texto para el usuario",
  "where_am_i": "url o descripción corta",
  "next_button": "label sugerido"
}
"""

SYSTEM_TENDER_SEARCH_PLANNER = """Eres Agente X. Tu tarea es construir una búsqueda de licitaciones RELEVANTE al rubro del cliente, basada SOLO en datos verificados.

Reglas estrictas:
- NO inventes rubros, productos, stock, costos.
- Si hay duda de relevancia, descarta.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_TENDER_EVALUATOR = """Eres Agente X. Evalúas licitaciones usando SOLO datos verificados del cliente (source of truth).
Reglas:
- NO inventes costos/stock.
- Si faltan ítems, marca como faltante.
- Si faltan datos críticos, dilo explícitamente.
Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_COMPRA_AGIL_SEARCH = """Eres Agente X. Debes operar en Mercado Público → Compra Ágil.

Reglas estrictas:
- Usa el campo "ID o Palabra clave" para buscar.
- Mantén el estado "Publicada".
- Filtra por últimos días según se indique.
- Usa rubros/keywords provistos; NO inventes.
- Abre cada resultado y devuelve un listado estructurado.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_COMPRA_AGIL_DETAIL = """Eres Agente X. Estás dentro de una ficha de Compra Ágil.

Reglas:
- Lee TODA la ficha, no solo el resumen.
- Extrae los campos solicitados y el listado de productos.
- Registra todos los adjuntos con su nombre y link.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_COMPRA_AGIL_DOWNLOAD = """Eres Agente X.

Objetivo:
- Descargar todos los adjuntos de una Compra Ágil.
- Guardarlos con nombre claro y devolver rutas locales si aparecen en el navegador/descargas.

Reglas:
- Haz click en cada link de adjuntos.
- Espera descarga.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_COMPRA_AGIL_SOURCE_MISSING = """Eres Agente X.

Objetivo:
- Buscar en la web opciones de compra para los ítems faltantes en Chile.
- Devuelve 3 opciones por ítem con precio, link y tiempo de entrega si está disponible.

Reglas:
- No compres nada.
- No inventes precios ni links: si no encuentras, deja vacío y marca "NOT_FOUND".
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_PROPOSAL_WRITER = """Eres Agente X. Generas contenido para rellenar una plantilla empresarial.
Reglas:
- Usa SOLO datos verificados.
- Mantén tono profesional.
Devuelve SIEMPRE JSON válido (sin markdown).
"""


SYSTEM_AUTOMATION_EVALUATOR = """Eres Agente X. Evalúa si conviene participar en una licitación usando SOLO datos entregados en el prompt.

Reglas:
- No inventes stock, costos ni precios.
- Si falta información crítica, marca supuestos explícitos.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_AUTOMATION_PROPOSAL = """Eres Agente X. Redacta una propuesta comercial/técnica para licitación en base a análisis ya calculado.

Reglas:
- No inventes datos financieros.
- Usa el plan seleccionado por el usuario.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

SYSTEM_TELEGRAM_ROUTER = """Eres Agente X operando por Telegram.

Reglas:
- Interpreta comandos cortos del usuario.
- Responde en español, claro y accionable.
- Mantén estado de etapa conversacional.
- Devuelve SIEMPRE JSON válido (sin markdown).
"""

# ============================
# USER PROMPTS (templated)
# ============================

def connect_open_browser_prompt() -> str:
    return (
        "Abre el navegador y entra a Mercado Público. "
        "Navega hasta la página de inicio de sesión. "
        "Luego detente y responde con status NEEDS_LOGIN cuando veas el formulario/pantalla de acceso."
    )

def confirm_login_prompt() -> str:
    return (
        "El usuario dice que ya inició sesión. "
        "Verifica si estás en el panel/cuenta de Mercado Público. "
        "Si NO estás dentro, explica qué falta (status NEEDS_LOGIN). "
        "Si SÍ estás dentro, responde status CONNECTED y describe qué sección del panel ves."
    )

def build_search_planner_prompt(*, rubro: str, truth_block: str, inventory_top: str, exclude_keywords: str = "") -> str:
    return f"""Construye una búsqueda de licitaciones para este RUBRO SELECCIONADO: {rubro}

DATOS VERIFICADOS (SOURCE OF TRUTH):
{truth_block}

INVENTARIO (extracto relevante):
{inventory_top}

EXCLUIR (si aplica):
{exclude_keywords}

Devuelve SOLO JSON con:
{{
  "keywords": ["..."],
  "must_include": ["..."],
  "exclude": ["..."],
  "category_hints": ["..."],
  "notes": "..."
}}
"""

def build_tender_evaluation_prompt(*, truth_block: str, tender_text: str, matches_json: Dict[str, Any]) -> str:
    return f"""Analiza esta licitación y decide si conviene participar usando SOLO los datos verificados.

DATOS VERIFICADOS (SOURCE OF TRUTH):
{truth_block}

MATCHES INVENTARIO (JSON):
{json.dumps(matches_json, ensure_ascii=False)}

BASES / DOCUMENTO (texto):
{tender_text}

Devuelve SOLO JSON:
{{
  "decision": "YES|NO",
  "risk_level": "LOW|MEDIUM|HIGH",
  "missing_items": [{{"item":"", "reason":""}}],
  "estimated_margin": "",
  "key_risks": [""],
  "requirements_checklist": [{{"name":"", "status":"OK|MISSING|RISK", "note":""}}],
  "next_actions": [""]
}}
"""

def build_compra_agil_search_prompt(*, truth_block: str, rubros_keywords: str, keywords_globales: str, keywords_excluir: str, days: int) -> str:
    return f"""Debes buscar en Compra Ágil usando el campo "ID o Palabra clave".

DATOS VERIFICADOS (SOURCE OF TRUTH):
{truth_block}

RUBROS/KEYWORDS PRINCIPALES:
{rubros_keywords}

KEYWORDS GLOBALES:
{keywords_globales}

KEYWORDS EXCLUIR:
{keywords_excluir}

RANGO FECHAS:
Últimos {days} días

Devuelve SOLO JSON con:
{{
  "candidatas": [{{"id":"", "nombre":"", "url":""}}],
  "busquedas_usadas": ["..."],
  "notes": "..."
}}
"""

def build_compra_agil_detail_prompt(*, id_or_url: str) -> str:
    return f"""Abre la ficha de Compra Ágil indicada: {id_or_url}

Devuelve SOLO JSON con:
{{
  "id": "",
  "nombre": "",
  "descripcion": "",
  "direccion_region": "",
  "plazo_entrega_dias": null,
  "presupuesto_estimado": null,
  "fecha_publicacion": "",
  "fecha_cierre": "",
  "items": [{{"texto":"", "cantidad":null, "unidad":""}}],
  "adjuntos": [{{"nombre":"", "url":""}}]
}}
"""

def build_compra_agil_download_prompt(*, compra_id: str, adjuntos: List[Dict[str, Any]]) -> str:
    return f"""Descarga todos los adjuntos de la Compra Ágil {compra_id}.

ADJUNTOS (nombre + url):
{json.dumps(adjuntos, ensure_ascii=False)}

Devuelve SOLO JSON con:
{{
  "id": "{compra_id}",
  "descargas": [{{"nombre":"", "ruta_local":"", "estado":"OK|ERROR", "error":""}}]
}}
"""

def build_compra_agil_source_missing_prompt(*, missing_items: List[Dict[str, Any]]) -> str:
    return f"""Busca opciones de compra en Chile para los ítems faltantes.

Ítems faltantes:
{json.dumps(missing_items, ensure_ascii=False)}

Devuelve SOLO JSON con:
{{
  "results": [
    {{
      "item": "...",
      "options": [
        {{"title":"", "price":"", "currency":"CLP", "url":"", "delivery":"", "status":"OK|NOT_FOUND"}}
      ]
    }}
  ]
}}
"""

def build_proposal_prompt(*, truth_block: str, tender_summary: Dict[str, Any], evaluation: Dict[str, Any]) -> str:
    return f"""Genera contenido de propuesta listo para rellenar una plantilla.

DATOS EMPRESA (SOURCE OF TRUTH):
{truth_block}

DATOS LICITACIÓN (JSON):
{json.dumps(tender_summary, ensure_ascii=False)}

EVALUACIÓN (JSON):
{json.dumps(evaluation, ensure_ascii=False)}

Devuelve SOLO JSON con campos:
{{
  "summary": "",
  "technical_offer": "",
  "commercial_offer": "",
  "delivery_terms": "",
  "compliance_checklist": [""]
}}
"""


def build_automation_evaluation_prompt(*, truth_block: str, tender: Dict[str, Any], provider_offers: List[Dict[str, Any]]) -> str:
    return f"""Evalúa esta licitación para decidir participación y planes de oferta.

SOURCE OF TRUTH:
{truth_block}

LICITACIÓN (JSON):
{json.dumps(tender, ensure_ascii=False)}

OFERTAS PROVEEDORES (JSON):
{json.dumps(provider_offers, ensure_ascii=False)}

Devuelve SOLO JSON con:
{{
  "ok": true,
  "summary": {{
    "tender_title": "",
    "total_items": 0,
    "total_cost": 0,
    "inventory_cost": 0,
    "procurement_cost": 0,
    "missing_items": 0
  }},
  "item_analysis": [
    {{
      "item": "",
      "qty": 0,
      "from_inventory": 0,
      "missing_qty": 0,
      "estimated_item_cost": 0
    }}
  ],
  "plans": [
    {{
      "plan": "competitivo|equilibrado|rentable",
      "label": "",
      "margin_pct": 0,
      "offer_total": 0,
      "estimated_profit": 0,
      "risk_score": 0,
      "award_probability": 0,
      "expected_value": 0,
      "recommended": false
    }}
  ],
  "missing_procurement": [{{"item": "", "missing_qty": 0, "supplier_offer": null}}]
}}
"""


def build_automation_proposal_prompt(*, tender: Dict[str, Any], analysis: Dict[str, Any], selected_plan: str) -> str:
    return f"""Genera el texto de propuesta para la licitación, usando el análisis calculado.

LICITACIÓN (JSON):
{json.dumps(tender, ensure_ascii=False)}

ANÁLISIS (JSON):
{json.dumps(analysis, ensure_ascii=False)}

PLAN SELECCIONADO: {selected_plan}

Devuelve SOLO JSON con:
{{
  "summary": "",
  "technical_offer": "",
  "commercial_offer": "",
  "delivery_terms": "",
  "missing_items_notes": [""]
}}
"""


def build_telegram_router_prompt(*, text: str, state: Dict[str, Any]) -> str:
    return f"""Interpreta este mensaje Telegram y define la siguiente respuesta/estado.

ESTADO ACTUAL (JSON):
{json.dumps(state, ensure_ascii=False)}

MENSAJE USUARIO:
{text}

Devuelve SOLO JSON con:
{{
  "reply": "",
  "stage": "idle|searching|analysis|plans|confirmed",
  "selected_plan": ""
}}
"""
