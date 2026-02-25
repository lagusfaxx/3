import os
import json
import requests
import streamlit as st
import pandas as pd

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Agente X — Demo Local", layout="wide")

def api_get(path: str, params=None):
    r = requests.get(f"{API_URL}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()

def api_post(path: str, payload: dict):
    r = requests.post(f"{API_URL}{path}", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()

def pretty_json(obj):
    st.code(json.dumps(obj, ensure_ascii=False, indent=2), language="json")

# ============================
# Header
# ============================
st.markdown("## 🧠 Agente X — Panel Operativo (Demo Local)")
st.caption("Sin chat libre: todo funciona con botones y opciones. Por detrás se envían prompts preestablecidos a OpenClaw.")

# Demo users
with st.sidebar:
    st.markdown("### 👤 Usuario demo")
    user_id = st.selectbox("Selecciona usuario", ["demo1", "demo2", "demo3"], index=0)
    st.session_state["user_id"] = user_id

    st.markdown("### 🔧 Backend")
    st.write(f"API: {API_URL}")

tabs = st.tabs(["1) Conectar", "2) Empresa e Inventario", "3) Compra Ágil", "4) Analizar PDF", "5) Historial / Estado"])

# ============================
# 1) Conectar (browser workflow)
# ============================
with tabs[0]:
    st.markdown("### Conectar Mercado Público (modo local)")
    st.info("Este flujo abre el navegador y deja el login para que lo hagas tú manualmente. Luego presionas 'Ya inicié sesión'.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🌐 Abrir navegador e ir a Mercado Público", use_container_width=True):
            out = api_post("/actions/connect/open-browser", {
                "user_id": user_id,
                "action": "connect_open_browser",
                "payload": {}
            })
            st.success("Acción enviada.")
            pretty_json(out)

    with col2:
        if st.button("✅ Ya inicié sesión (confirmar)", use_container_width=True):
            out = api_post("/actions/connect/confirm", {
                "user_id": user_id,
                "action": "connect_confirm",
                "payload": {}
            })
            pretty_json(out)

    st.markdown("#### Estado actual")
    state = api_get("/connector/state", params={"user_id": user_id})
    pretty_json(state)

# ============================
# 2) Empresa + Inventario
# ============================
with tabs[1]:
    st.markdown("### Datos de empresa (Source of Truth)")

    company = api_get("/company", params={"user_id": user_id})
    c1, c2, c3 = st.columns(3)
    with c1:
        company_name = st.text_input("Nombre empresa", value=company.get("company_name",""))
        rut = st.text_input("RUT", value=company.get("rut",""))
    with c2:
        categories = st.text_input("Rubros/categorías (coma)", value=company.get("categories",""))
        delivery_days = st.text_input("Plazos típicos de entrega", value=company.get("delivery_days",""))
    with c3:
        margin_min = st.number_input("Margen mínimo (%)", value=float(company.get("margin_min",0.0)), step=1.0)
        margin_target = st.number_input("Margen objetivo (%)", value=float(company.get("margin_target",0.0)), step=1.0)

    c4, c5, c6 = st.columns(3)
    with c4:
        rubros_keywords = st.text_input("Rubros keywords (coma)", value=company.get("rubros_keywords",""))
    with c5:
        keywords_globales = st.text_input("Keywords globales (coma)", value=company.get("keywords_globales",""))
    with c6:
        keywords_excluir = st.text_input("Keywords excluir (coma)", value=company.get("keywords_excluir",""))

    risk_rules = st.text_area("Reglas de riesgo (1 por línea)", value=company.get("risk_rules",""), height=140)

    if st.button("💾 Guardar empresa", use_container_width=True):
        out = api_post("/company", {
            "user_id": user_id,
            "company_name": company_name,
            "rut": rut,
            "categories": categories,
            "rubros_keywords": rubros_keywords,
            "keywords_globales": keywords_globales,
            "keywords_excluir": keywords_excluir,
            "margin_min": margin_min,
            "margin_target": margin_target,
            "delivery_days": delivery_days,
            "risk_rules": risk_rules,
        })
        st.success("Guardado.")
        pretty_json(out)

    st.divider()
    st.markdown("### Inventario (CSV)")

    st.caption("Columnas recomendadas: sku,name,synonyms,cost,price,stock,restock_days,supplier")
    file = st.file_uploader("Subir CSV de inventario", type=["csv"])
    if file is not None:
        files = {"file": (file.name, file.getvalue(), "text/csv")}
        r = requests.post(f"{API_URL}/inventory/upload", params={"user_id": user_id}, files=files, timeout=120)
        r.raise_for_status()
        st.success("Inventario cargado.")
        pretty_json(r.json())

    inv = api_get("/inventory", params={"user_id": user_id})
    if inv:
        df = pd.DataFrame(inv)
        st.dataframe(df, use_container_width=True, height=280)
    else:
        st.warning("Aún no hay inventario para este usuario.")

# ============================
# 3) Buscar licitaciones (prompts fixed)
# ============================
with tabs[2]:
    st.markdown("### Compra Ágil (descubrimiento + pre-filtro)")
    company = api_get("/company", params={"user_id": user_id})
    default_rubros = company.get("rubros_keywords","") or company.get("categories","")
    default_globales = company.get("keywords_globales","")
    default_excluir = company.get("keywords_excluir","")

    c1, c2 = st.columns([2, 1])
    with c1:
        rubros_keywords = st.text_input("Rubros/keywords principales (coma)", value=default_rubros, key="compra_rubros_keywords")
        keywords_globales = st.text_input("Keywords globales (coma)", value=default_globales, key="compra_keywords_globales")
    with c2:
        keywords_excluir = st.text_input("Keywords excluir (coma)", value=default_excluir, key="compra_keywords_excluir")
        days = st.number_input("Últimos días", min_value=1, max_value=7, value=2, step=1, key="compra_days")

    if st.button("🔍 Buscar en Compra Ágil", use_container_width=True):
        out = api_post("/compra-agil/search", {
            "user_id": user_id,
            "action": "compra_agil_search",
            "payload": {
                "rubros_keywords": rubros_keywords,
                "keywords_globales": keywords_globales,
                "keywords_excluir": keywords_excluir,
                "days": int(days),
            }
        })
        st.session_state["last_compra_agil_search"] = out
        st.success("Búsqueda enviada.")
        pretty_json(out)

    search = st.session_state.get("last_compra_agil_search", {}).get("result", {})
    candidatas = search.get("candidatas") or []
    if candidatas:
        st.markdown("### Resultados (candidatas)")
        pretty_json(candidatas)

    st.divider()
    st.markdown("### Procesar Compra Ágil (1 click)")
    id_or_url = st.text_input("ID o URL de compra", value=(candidatas[0].get("url") if candidatas else ""))

    st.markdown("### Filtros de adjuntos")
    cfa, cfb, cfc = st.columns(3)
    with cfa:
        include_pdf = st.checkbox("PDF", value=True, key="filter_pdf")
    with cfb:
        include_excel = st.checkbox("Excel (xlsx/xls)", value=True, key="filter_excel")
    with cfc:
        include_csv = st.checkbox("CSV", value=False, key="filter_csv")

    if st.button("⚡ Procesar Compra Ágil", use_container_width=True, disabled=not id_or_url):
        # 1) Leer ficha
        detail_resp = api_post("/compra-agil/parse_detail", {
            "user_id": user_id,
            "action": "compra_agil_parse_detail",
            "payload": {"id_or_url": id_or_url}
        })
        st.session_state["last_compra_agil_detail"] = detail_resp
        pretty_json(detail_resp)

        detail = detail_resp.get("result", {})
        # 2) Descargar adjuntos
        dl = api_post("/compra-agil/download_attachments", {
            "user_id": user_id,
            "action": "compra_agil_download_attachments",
            "payload": {"id": detail.get("id",""), "adjuntos": detail.get("adjuntos", [])}
        })
        st.session_state["last_compra_agil_downloads"] = dl
        pretty_json(dl)

        # 3) Analizar adjuntos (si hay rutas)
        descargas = dl.get("result", {}).get("descargas") or []
        rutas = [d.get("ruta_local") for d in descargas if d.get("ruta_local")]
        rutas_filtradas = []
        for r in rutas:
            ext = str(r).lower().split(".")[-1]
            if ext == "pdf" and include_pdf:
                rutas_filtradas.append(r)
            if ext in ["xlsx", "xlsm", "xls"] and include_excel:
                rutas_filtradas.append(r)
            if ext == "csv" and include_csv:
                rutas_filtradas.append(r)

        if rutas_filtradas:
            an = api_post("/compra-agil/analyze_attachments", {
                "user_id": user_id,
                "action": "compra_agil_analyze_attachments",
                "payload": {"paths": rutas_filtradas}
            })
            st.session_state["last_compra_agil_analysis"] = an
            pretty_json(an)
        else:
            st.warning("No hay rutas válidas para analizar.")

        # 4) Decisión
        dv = api_post("/compra-agil/decision", {
            "user_id": user_id,
            "action": "compra_agil_decision",
            "payload": {"ficha": detail}
        })
        st.session_state["last_compra_agil_decision"] = dv
        pretty_json(dv)

    detail = st.session_state.get("last_compra_agil_detail", {}).get("result", {})
    if detail:
        st.markdown("### Ficha parseada")
        pretty_json(detail)

        if st.button("⬇️ Descargar adjuntos", use_container_width=True):
            out = api_post("/compra-agil/download_attachments", {
                "user_id": user_id,
                "action": "compra_agil_download_attachments",
                "payload": {"id": detail.get("id",""), "adjuntos": detail.get("adjuntos", [])}
            })
            st.session_state["last_compra_agil_downloads"] = out
            st.success("Descarga solicitada.")
            pretty_json(out)

        if st.button("✅ Cruce con inventario y decisión", use_container_width=True):
            out = api_post("/compra-agil/decision", {
                "user_id": user_id,
                "action": "compra_agil_decision",
                "payload": {"ficha": detail}
            })
            st.session_state["last_compra_agil_decision"] = out
            st.success("Decisión lista.")
            pretty_json(out)

        downloads = st.session_state.get("last_compra_agil_downloads", {}).get("result", {})
        if downloads:
            st.markdown("### Analizar adjuntos (PDF/Excel/CSV)")
            descargas = downloads.get("descargas") or []
            rutas = [d.get("ruta_local") for d in descargas if d.get("ruta_local")]
            rutas_filtradas = []
            for r in rutas:
                ext = str(r).lower().split(".")[-1]
                if ext == "pdf" and include_pdf:
                    rutas_filtradas.append(r)
                if ext in ["xlsx", "xlsm", "xls"] and include_excel:
                    rutas_filtradas.append(r)
                if ext == "csv" and include_csv:
                    rutas_filtradas.append(r)

            paths_input = st.text_area("Rutas adjuntos (1 por línea)", value="\n".join(rutas_filtradas), height=120)
            if st.button("🧾 Analizar adjuntos", use_container_width=True, disabled=not paths_input.strip()):
                paths = [x.strip() for x in paths_input.splitlines() if x.strip()]
                out = api_post("/compra-agil/analyze_attachments", {
                    "user_id": user_id,
                    "action": "compra_agil_analyze_attachments",
                    "payload": {"paths": paths}
                })
                st.session_state["last_compra_agil_analysis"] = out
                st.success("Análisis listo.")
                pretty_json(out)

        decision = st.session_state.get("last_compra_agil_decision", {}).get("result", {})
        if decision:
            st.markdown("### Faltantes: búsqueda web (opcional)")
            max_missing = st.number_input("Máx. ítems a buscar", min_value=1, max_value=5, value=1, step=1)
            faltantes = decision.get("items_faltantes") or []
            if len(faltantes) > 0:
                payload_items = [{"item": f.get("item")} for f in faltantes[: int(max_missing)]]
                if st.button("🌐 Buscar opciones para faltantes", use_container_width=True):
                    out = api_post("/compra-agil/source_missing", {
                        "user_id": user_id,
                        "action": "compra_agil_source_missing",
                        "payload": {"missing_items": payload_items}
                    })
                    st.session_state["last_compra_agil_sourcing"] = out
                    st.success("Búsqueda solicitada.")
                    pretty_json(out)
            else:
                st.info("No hay ítems faltantes según el cruce.")


# ============================
# 4) Analizar PDF (evaluación + propuesta + PDF)
# ============================
with tabs[3]:
    st.markdown("### Analizar bases PDF → Evaluar → Propuesta → PDF")

    pdf = st.file_uploader("Sube un PDF de bases/lic", type=["pdf"])
    required_items_text = st.text_area("Ítems requeridos (1 por línea, opcional)", placeholder="Monitor 24\nMonitor 27\n...", height=120)

    if st.button("🧾 Analizar (IA) + Evaluar (inventario)", use_container_width=True, disabled=(pdf is None)):
        # 1) Extract text via backend /analyze (ya existe), pero aquí hacemos extract local -> analyze endpoint
        files = {"file": (pdf.name, pdf.getvalue(), "application/pdf")}
        r = requests.post(f"{API_URL}/analyze", params={"user_id": user_id}, files=files, timeout=180)
        r.raise_for_status()
        analysis = r.json()
        st.success("Análisis base OK.")
        st.session_state["last_analysis"] = analysis
        pretty_json(analysis)

        tender_text = analysis.get("text_excerpt","") or analysis.get("text","") or ""
        required_items = [x.strip() for x in required_items_text.splitlines() if x.strip()]
        ev = api_post("/tenders/evaluate", {
            "user_id": user_id,
            "action": "tenders_evaluate",
            "payload": {"tender_text": tender_text, "required_items": required_items}
        })
        st.session_state["last_evaluation"] = ev
        st.subheader("📌 Evaluación")
        pretty_json(ev)

    if "last_evaluation" in st.session_state:
        st.divider()
        st.markdown("### Generar propuesta (JSON) y PDF")
        if st.button("📝 Generar propuesta", use_container_width=True):
            tender_summary = {"source": "pdf", "filename": (pdf.name if pdf else "")}
            ev_result = st.session_state["last_evaluation"].get("result", {})
            out = api_post("/tenders/proposal", {
                "user_id": user_id,
                "action": "tenders_proposal",
                "payload": {"tender_summary": tender_summary, "evaluation": ev_result}
            })
            st.session_state["last_proposal"] = out
            pretty_json(out)

        if st.button("📥 Descargar informe PDF", use_container_width=True):
            # Usa /report existente: requiere payload con company + inventory + analysis + evaluation
            company = api_get("/company", params={"user_id": user_id})
            inv = api_get("/inventory", params={"user_id": user_id})
            analysis = st.session_state.get("last_analysis", {})
            evaluation = st.session_state.get("last_evaluation", {}).get("result", {})
            payload = {
                "company": company,
                "inventory": inv,
                "analysis": analysis,
                "evaluation": evaluation,
                "proposal": st.session_state.get("last_proposal", {}).get("result", {}),
            }
            rr = requests.post(f"{API_URL}/report", json=payload, timeout=180)
            rr.raise_for_status()
            st.download_button("Descargar PDF", data=rr.content, file_name="informe_agente_x.pdf", mime="application/pdf", use_container_width=True)

# ============================
# 5) Estado
# ============================
with tabs[4]:
    st.markdown("### Historial (Jobs)")
    c1, c2 = st.columns([1, 2])
    with c1:
        limit = st.number_input("Máx. registros", min_value=10, max_value=200, value=50, step=10)
        if st.button("🔄 Actualizar", use_container_width=True):
            st.session_state.pop("jobs_cache", None)

    jobs = st.session_state.get("jobs_cache")
    if jobs is None:
        try:
            jobs = api_get("/jobs", params={"user_id": user_id, "limit": int(limit)})
        except Exception as e:
            jobs = []
            st.error(f"No pude cargar jobs: {e}")
        st.session_state["jobs_cache"] = jobs

    if jobs:
        df = pd.DataFrame(jobs)
        st.dataframe(df, use_container_width=True, height=260)

        with c2:
            ids = [str(j["id"]) for j in jobs]
            chosen = st.selectbox("Ver detalle", ids, index=0)
            detail = api_get(f"/jobs/{chosen}")
            st.subheader(f"Job #{chosen} — {detail.get('action')} — {detail.get('status')}")
            colA, colB = st.columns(2)
            with colA:
                st.caption("Payload")
                st.code(detail.get("payload_json") or "(vacío)")
                st.caption("Error")
                st.code(detail.get("error") or "(sin error)")
            with colB:
                st.caption("Result")
                st.code(detail.get("result_json") or "(vacío)")
                st.caption("Raw")
                st.code((detail.get("raw") or "")[:6000] or "(vacío)")
    else:
        st.info("Aún no hay historial para este usuario.")

    st.divider()
    st.markdown("### Estado conector")
    state = api_get("/connector/state", params={"user_id": user_id})
    pretty_json(state)
    st.caption("Tip: si el gateway se reinicia, reintenta Conectar → Confirmar.")
