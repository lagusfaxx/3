#!/usr/bin/env bash
set -e

if [ ! -d ".venv" ]; then
  python -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo "Inicia backend en :8000 y frontend en :8501 (abre otra terminal para streamlit)."
uvicorn backend.app.main:app --reload --port 8000
