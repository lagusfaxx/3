from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .storage import match_inventory


@dataclass
class PlanConfig:
    key: str
    label: str
    margin_factor: float
    competitiveness_bonus: float


PLAN_CONFIGS = [
    PlanConfig("competitivo", "Plan competitivo", 0.75, 0.12),
    PlanConfig("equilibrado", "Plan equilibrado", 1.0, 0.0),
    PlanConfig("rentable", "Plan mayor ganancia", 1.35, -0.1),
]


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _find_best_offer(item_name: str, missing_qty: int, provider_offers: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best: Optional[Dict[str, Any]] = None
    needle = item_name.lower()
    for offer in provider_offers:
        name = str(offer.get("name") or "").lower()
        if needle not in name and name not in needle:
            continue
        stock = _to_int(offer.get("stock"), 0)
        if stock < missing_qty:
            continue
        if best is None or _to_float(offer.get("unit_cost"), 10**9) < _to_float(best.get("unit_cost"), 10**9):
            best = offer
    return best


def evaluate_tender_opportunity(
    *,
    tender: Dict[str, Any],
    inventory: List[Dict[str, Any]],
    company: Dict[str, Any],
    provider_offers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    provider_offers = provider_offers or []
    items = tender.get("items") or []
    if not items:
        return {
            "ok": False,
            "error": "La licitación no tiene ítems para evaluar.",
            "plans": [],
            "item_analysis": [],
        }

    required_names = [str(it.get("name") or it.get("item") or "").strip() for it in items]
    matching = match_inventory(required_names, inventory, top_k=1)

    margin_target = _to_float(company.get("margin_target"), 18.0) / 100.0
    margin_min = _to_float(company.get("margin_min"), 8.0) / 100.0

    item_analysis: List[Dict[str, Any]] = []
    inventory_cost_total = 0.0
    procurement_cost_total = 0.0
    missing_count = 0

    for src, match in zip(items, matching):
        req_name = str(src.get("name") or src.get("item") or "Ítem").strip()
        qty = max(1, _to_int(src.get("qty"), 1))
        best_inv = (match.get("matches") or [None])[0]
        inv_stock = _to_int((best_inv or {}).get("stock"), 0)
        inv_unit_cost = _to_float((best_inv or {}).get("cost"), 0.0)
        use_from_stock = min(inv_stock, qty)
        missing_qty = max(qty - use_from_stock, 0)

        inv_cost = use_from_stock * inv_unit_cost
        inventory_cost_total += inv_cost

        provider = _find_best_offer(req_name, missing_qty, provider_offers) if missing_qty > 0 else None
        provider_unit_cost = _to_float((provider or {}).get("unit_cost"), 0.0)
        provider_cost = missing_qty * provider_unit_cost
        procurement_cost_total += provider_cost

        if missing_qty > 0:
            missing_count += 1

        item_analysis.append(
            {
                "item": req_name,
                "qty": qty,
                "from_inventory": use_from_stock,
                "missing_qty": missing_qty,
                "inventory_match": best_inv,
                "supplier_offer": provider,
                "estimated_item_cost": round(inv_cost + provider_cost, 2),
            }
        )

    total_cost = round(inventory_cost_total + procurement_cost_total, 2)
    missing_ratio = missing_count / max(len(items), 1)
    risk_score = min(1.0, 0.2 + 0.55 * missing_ratio + 0.25 * (1 if _to_int(tender.get("deadline_days"), 10) <= 3 else 0))

    plans: List[Dict[str, Any]] = []
    for cfg in PLAN_CONFIGS:
        margin = max(margin_min, margin_target * cfg.margin_factor)
        offer_total = round(total_cost * (1 + margin), 2)
        profit = round(offer_total - total_cost, 2)
        award_probability = max(0.08, min(0.92, 0.58 - risk_score * 0.28 + cfg.competitiveness_bonus))
        expected_value = round(profit * award_probability, 2)
        plans.append(
            {
                "plan": cfg.key,
                "label": cfg.label,
                "margin_pct": round(margin * 100, 2),
                "offer_total": offer_total,
                "estimated_profit": profit,
                "risk_score": round(risk_score, 3),
                "award_probability": round(award_probability, 3),
                "expected_value": expected_value,
                "recommended": False,
            }
        )

    if plans:
        best_idx = max(range(len(plans)), key=lambda i: plans[i]["expected_value"])
        plans[best_idx]["recommended"] = True

    return {
        "ok": True,
        "summary": {
            "tender_title": tender.get("title") or "Licitación",
            "total_items": len(items),
            "total_cost": total_cost,
            "inventory_cost": round(inventory_cost_total, 2),
            "procurement_cost": round(procurement_cost_total, 2),
            "missing_items": missing_count,
        },
        "item_analysis": item_analysis,
        "plans": plans,
        "missing_procurement": [
            {
                "item": row["item"],
                "missing_qty": row["missing_qty"],
                "supplier_offer": row.get("supplier_offer"),
            }
            for row in item_analysis
            if row["missing_qty"] > 0
        ],
    }


def telegram_command_router(text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    msg = (text or "").strip()
    if not msg:
        return {"reply": "Envía un comando: /buscar, /analizar, /planes o /confirmar"}

    if msg.startswith("/buscar"):
        state["stage"] = "searching"
        return {"reply": "🔎 Búsqueda iniciada. Te avisaré cuando encuentre licitaciones compatibles."}

    if msg.startswith("/analizar"):
        state["stage"] = "analysis"
        return {"reply": "📊 Ejecutando análisis de stock, costos, margen, riesgo y probabilidad de adjudicación."}

    if msg.startswith("/planes"):
        state["stage"] = "plans"
        return {"reply": "💡 Puedes elegir: competitivo, equilibrado o rentable. Usa /confirmar <plan>."}

    if msg.startswith("/confirmar"):
        selected = msg.replace("/confirmar", "").strip() or "equilibrado"
        state["selected_plan"] = selected
        state["stage"] = "confirmed"
        return {"reply": f"✅ Plan '{selected}' confirmado. Generaré PDF y enviaré la propuesta."}

    return {"reply": "Comando no reconocido. Usa /buscar, /analizar, /planes, /confirmar"}
