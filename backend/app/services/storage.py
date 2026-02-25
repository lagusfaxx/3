from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import re
from pathlib import Path

from ..settings import settings

DB_PATH = Path(getattr(settings, "db_path", "backend/app/data/app.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def _ensure_columns(con: sqlite3.Connection, table: str, columns: Dict[str, str]) -> None:
    cur = con.execute(f"PRAGMA table_info({table});")
    existing = {row[1] for row in cur.fetchall()}
    for name, ddl in columns.items():
        if name not in existing:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl};")
    con.commit()


# ==========================
# INIT DB (CORREGIDO)
# ==========================

def init_db() -> None:
    con = _conn()
    try:

        # Tabla empresa
        con.execute("""
        CREATE TABLE IF NOT EXISTS company_profile (
            user_id TEXT PRIMARY KEY,
            company_name TEXT,
            rut TEXT,
            categories TEXT,
            margin_min REAL,
            margin_target REAL,
            delivery_days TEXT,
            risk_rules TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """)

        # Tablas múltiples → executescript
        con.executescript("""
        CREATE TABLE IF NOT EXISTS connector_state (
            user_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            instructions TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS inventory_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            sku TEXT,
            name TEXT NOT NULL,
            synonyms TEXT,
            cost REAL,
            price REAL,
            stock INTEGER,
            restock_days INTEGER,
            supplier TEXT
        );

        -- Historial de ejecuciones (jobs) para modo SaaS
        CREATE TABLE IF NOT EXISTS job (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT,
            result_json TEXT,
            raw TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)

        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory_item(user_id);"
        )

        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_user_created ON job(user_id, created_at DESC);"
        )

        con.commit()

        _ensure_columns(con, "company_profile", {
            "rubros_keywords": "TEXT",
            "keywords_globales": "TEXT",
            "keywords_excluir": "TEXT",
        })

        _ensure_columns(con, "inventory_item", {
            "synonyms": "TEXT",
        })

    finally:
        con.close()


# ==========================
# JOBS (Historial)
# ==========================

def create_job(user_id: str, action: str, payload_json: str | None = None) -> int:
    init_db()
    con = _conn()
    try:
        cur = con.execute(
            "INSERT INTO job (user_id, action, status, payload_json) VALUES (?,?,?,?)",
            (user_id, action, "RUNNING", payload_json),
        )
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()


def finish_job(job_id: int, status: str, result_json: str | None = None, raw: str | None = None, error: str | None = None) -> None:
    init_db()
    con = _conn()
    try:
        con.execute(
            """
            UPDATE job
            SET status=?, result_json=?, raw=?, error=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (status, result_json, raw, error, int(job_id)),
        )
        con.commit()
    finally:
        con.close()


def list_jobs(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    init_db()
    con = _conn()
    try:
        rows = con.execute(
            """
            SELECT id,user_id,action,status,created_at,updated_at
            FROM job
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, int(limit), int(offset)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    con = _conn()
    try:
        row = con.execute(
            "SELECT * FROM job WHERE id=?",
            (int(job_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


# ==========================
# COMPANY
# ==========================

def get_company(user_id: str) -> Optional[Dict[str, Any]]:
    init_db()

    con = _conn()
    try:
        row = con.execute(
            "SELECT * FROM company_profile WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        con.close()


def upsert_company(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:

    init_db()

    con = _conn()

    try:

        existing = get_company(user_id)

        payload = {
            "company_name": data.get("company_name") or "",
            "rut": data.get("rut") or "",
            "categories": data.get("categories") or "",
            "rubros_keywords": data.get("rubros_keywords") or "",
            "keywords_globales": data.get("keywords_globales") or "",
            "keywords_excluir": data.get("keywords_excluir") or "",
            "margin_min": float(data.get("margin_min") or 0),
            "margin_target": float(data.get("margin_target") or 0),
            "delivery_days": data.get("delivery_days") or "",
            "risk_rules": data.get("risk_rules") or "",
        }

        if existing:

            con.execute("""
                UPDATE company_profile
                SET company_name=?,
                    rut=?,
                    categories=?,
                    rubros_keywords=?,
                    keywords_globales=?,
                    keywords_excluir=?,
                    margin_min=?,
                    margin_target=?,
                    delivery_days=?,
                    risk_rules=?,
                    updated_at=datetime('now')
                WHERE user_id=?
            """,
                (
                    payload["company_name"],
                    payload["rut"],
                    payload["categories"],
                    payload["rubros_keywords"],
                    payload["keywords_globales"],
                    payload["keywords_excluir"],
                    payload["margin_min"],
                    payload["margin_target"],
                    payload["delivery_days"],
                    payload["risk_rules"],
                    user_id,
                )
            )

        else:

            con.execute("""
                INSERT INTO company_profile
                (user_id,company_name,rut,categories,
                 rubros_keywords,keywords_globales,keywords_excluir,
                 margin_min,margin_target,delivery_days,risk_rules)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
                (
                    user_id,
                    payload["company_name"],
                    payload["rut"],
                    payload["categories"],
                    payload["rubros_keywords"],
                    payload["keywords_globales"],
                    payload["keywords_excluir"],
                    payload["margin_min"],
                    payload["margin_target"],
                    payload["delivery_days"],
                    payload["risk_rules"],
                )
            )

        con.commit()

        return get_company(user_id)

    finally:
        con.close()


# ==========================
# INVENTORY
# ==========================

def list_inventory(user_id: str) -> List[Dict[str, Any]]:

    init_db()

    con = _conn()

    try:

        rows = con.execute("""

        SELECT sku,name,synonyms,cost,price,stock,
               restock_days,supplier

        FROM inventory_item
        WHERE user_id=?
        ORDER BY name ASC

        """,
            (user_id,)
        ).fetchall()

        return [dict(r) for r in rows]

    finally:
        con.close()


def replace_inventory(user_id: str, items: List[Dict[str, Any]]) -> int:

    init_db()

    con = _conn()

    try:

        con.execute(
            "DELETE FROM inventory_item WHERE user_id=?",
            (user_id,)
        )

        for it in items:

            con.execute("""

            INSERT INTO inventory_item
            (user_id,sku,name,synonyms,cost,price,
             stock,restock_days,supplier)

            VALUES (?,?,?,?,?,?,?,?,?)

            """,
                (
                    user_id,
                    it.get("sku"),
                    it.get("name"),
                    it.get("synonyms"),
                    it.get("cost"),
                    it.get("price"),
                    it.get("stock"),
                    it.get("restock_days"),
                    it.get("supplier"),
                )
            )

        con.commit()

        return len(items)

    finally:
        con.close()


# ==========================
# SOURCE OF TRUTH
# ==========================

def build_truth_block(user_id: str | Dict[str, Any], inv: Optional[List[Dict[str, Any]]] = None, max_items: int = 80) -> str:
    if isinstance(user_id, str):
        company = get_company(user_id) or {}
        inv = list_inventory(user_id)[:max_items]
        user_label = user_id
    else:
        company = dict(user_id)
        inv = (inv or [])[:max_items]
        user_label = company.get("user_id", "demo")

    lines: List[str] = []

    lines.append("### DATOS VERIFICADOS DEL CLIENTE")
    lines.append(f"Usuario: {user_label}")

    if company:

        lines.append(f"Empresa: {company.get('company_name')}")
        lines.append(f"Rubros: {company.get('categories')}")
        if company.get("rubros_keywords") or company.get("keywords_globales"):
            lines.append(f"Rubros keywords: {company.get('rubros_keywords')}")
            lines.append(f"Keywords globales: {company.get('keywords_globales')}")
            lines.append(f"Keywords excluir: {company.get('keywords_excluir')}")

    lines.append("")
    lines.append("Inventario:")

    if not inv:

        lines.append("- vacío")

    else:

        for it in inv:

            lines.append(
                f"- {it['name']} stock:{it['stock']} costo:{it['cost']}"
            )

    return "\n".join(lines)


# ==========================
# MATCHING
# ==========================

def _normalize(text: str) -> str:
    import unicodedata
    base = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join([c for c in base if not unicodedata.combining(c)])


def _tokenize(text: str) -> List[str]:
    norm = _normalize(text)
    return [t for t in re.split(r"[^a-z0-9]+", norm) if t]


def match_inventory(
    required_items: List[str],
    inventory: List[Dict[str, Any]],
    top_k: int = 3,
    boost_keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    inv_tokens = []
    boost_set = set(_tokenize(" ".join(boost_keywords or [])))
    for it in inventory:
        name = str(it.get("name") or "")
        synonyms = str(it.get("synonyms") or "")
        tokens = set(_tokenize(name + " " + synonyms))
        inv_tokens.append((it, tokens))

    for req in required_items:
        req_tokens = set(_tokenize(str(req)))
        scored = []
        for it, tokens in inv_tokens:
            if not req_tokens or not tokens:
                score = 0.0
            else:
                overlap = len(req_tokens & tokens)
                score = overlap / max(len(req_tokens), 1)
                if boost_set:
                    if (req_tokens & boost_set) and (tokens & boost_set):
                        score = min(1.0, score + 0.15)
            if score > 0:
                scored.append((score, it))

        scored.sort(key=lambda x: x[0], reverse=True)
        matches = []
        for score, it in scored[:top_k]:
            matches.append(
                {
                    "name": it.get("name"),
                    "sku": it.get("sku"),
                    "synonyms": it.get("synonyms"),
                    "stock": it.get("stock"),
                    "cost": it.get("cost"),
                    "price": it.get("price"),
                    "supplier": it.get("supplier"),
                    "score": score,
                }
            )

        results.append({"required": req, "matches": matches})

    return results


def inventory_compatibility(
    items: List[Dict[str, Any]],
    inventory: List[Dict[str, Any]],
    *,
    min_score: float = 0.4,
    boost_keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    total = len(items)
    if total == 0:
        return {
            "compat_score": 0,
            "items_cubiertos": [],
            "items_faltantes": [],
        }

    matches = match_inventory(
        [it.get("texto") or it.get("item") or it.get("name") or "" for it in items],
        inventory,
        top_k=1,
        boost_keywords=boost_keywords,
    )
    items_cubiertos = []
    items_faltantes = []

    for src, match in zip(items, matches):
        best = match.get("matches", [None])[0] if match.get("matches") else None
        if best and float(best.get("score") or 0) >= min_score and (best.get("stock") or 0) > 0:
            items_cubiertos.append({
                "item": src,
                "match": best,
            })
        else:
            items_faltantes.append({
                "item": src,
                "best_match": best,
            })

    compat_score = round(100 * len(items_cubiertos) / max(total, 1))

    return {
        "compat_score": compat_score,
        "items_cubiertos": items_cubiertos,
        "items_faltantes": items_faltantes,
    }


# ==========================
# CONNECTOR
# ==========================

def get_connector_state(user_id: str) -> Dict[str, Any]:

    init_db()

    with _conn() as con:

        cur = con.execute("""

        SELECT user_id,status,
               instructions,updated_at

        FROM connector_state
        WHERE user_id=?

        """,
            (user_id,)
        )

        row = cur.fetchone()

        if not row:

            return {
                "user_id": user_id,
                "status": "NOT_CONNECTED",
                "instructions": "",
                "updated_at": "",
            }

        return dict(row)


def set_connector_state(
        user_id: str,
        status: str,
        instructions: str = ""
):

    init_db()

    from datetime import datetime

    now = datetime.utcnow().isoformat()

    with _conn() as con:

        con.execute("""

        INSERT INTO connector_state
        (user_id,status,instructions,updated_at)

        VALUES (?,?,?,?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            status=excluded.status,
            instructions=excluded.instructions,
            updated_at=excluded.updated_at

        """,
            (user_id, status, instructions, now)
        )
