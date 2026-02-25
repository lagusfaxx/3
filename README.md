# Agente X (MVP local) — FastAPI + Streamlit + Gateway OpenClaw (opcional)

Este ZIP es un **MVP funcional** para ejecutar en tu PC una versión local del SaaS:
- **Backend**: FastAPI (API REST)
- **Frontend**: Streamlit (UI rápida tipo dashboard)
- **Extracción PDF**: pdfplumber
- **Gateway**: integración **opcional** con OpenClaw Gateway compatible con `/v1/chat/completions`
  - Por defecto apunta a `http://127.0.0.1:18789`

> Nota importante: por seguridad, este MVP **no compra nada**. Si habilitas el módulo de “suministro”, queda en modo **búsqueda/sugerencias** (puedes implementar compra real con aprobación humana).

---

## 1) Requisitos
- Python 3.10+ (recomendado 3.11)
- (Opcional) OpenClaw Gateway corriendo en `127.0.0.1:18789`

---

## 2) Instalación (Windows / Mac / Linux)

### A) Crear venv e instalar dependencias
```bash
cd AgenteX_SaaS_Local
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### B) Configurar variables (opcional)
Copia `.env.example` a `.env` y ajusta si quieres:
- `OPENCLAW_GATEWAY_TOKEN` (si tu gateway está protegido por token)
- `GATEWAY_URL`
- `USE_GATEWAY=true|false`

---

## 3) Ejecutar

### Terminal 1 — Backend (FastAPI)
```bash
uvicorn backend.app.main:app --reload --port 8000
```

### Terminal 2 — Frontend (Streamlit)
```bash
streamlit run frontend/streamlit_app.py --server.port 8501
```

- UI: http://localhost:8501
- API docs: http://localhost:8000/docs

---

## 4) Qué hace el MVP
- Subes un PDF de bases/lic.
- Extrae texto, lo resume, detecta **requisitos**, **riesgos**, y genera una **propuesta** en Markdown.
- Si `USE_GATEWAY=true`, usa el Gateway (OpenClaw) para “pensar”/redactar; si no, usa un motor local sencillo (heurísticas + plantillas) para que sea 100% runnable.

### Modo "SaaS" (local)
- La UI permite seleccionar `user_id` (demo1/demo2/demo3).
- El backend acepta `?user_id=` en la mayoría de endpoints (y también `X-User-Id` si prefieres header).
- Se guarda **historial de ejecuciones** en SQLite (`job`): acciones, estado, resultado, raw y errores.

Endpoints nuevos:
- `GET /jobs?user_id=demo1` → lista de jobs
- `GET /jobs/{id}` → detalle

---

## 5) Estructura
```
backend/
  app/
    main.py
    settings.py
    schemas.py
    services/
      pdf_extract.py
      gateway_client.py
      analysis.py
frontend/
  streamlit_app.py
```

---

## 6) Problemas típicos
- **pdfplumber falla**: instala `pypdfium2` o actualiza poppler según tu OS (raro en la mayoría de casos).
- **Gateway no responde**: deja `USE_GATEWAY=false` y el MVP sigue funcionando.

---

## 7) Próximos pasos
- Conectar autenticación (JWT), pagos y límites.
- Persistencia (Postgres + Prisma o SQLAlchemy).
- Skills reales (scraping proveedores, stock, etc.) con aprobación humana.


## Informe descargable (PDF)

- Después de analizar un PDF, puedes generar un **informe PDF** con el endpoint `POST /report` (lo usa el botón **Descargar informe PDF** en Streamlit).
