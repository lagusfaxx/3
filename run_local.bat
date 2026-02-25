@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
pip install -r requirements.txt

echo Inicia backend en http://localhost:8000
uvicorn backend.app.main:app --reload --port 8000
