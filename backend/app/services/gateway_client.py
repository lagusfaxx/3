from __future__ import annotations
import httpx
from typing import Optional, Dict, Any
from ..settings import settings

def _payload(user_message: str, system: Optional[str] = None) -> Dict[str, Any]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})

    payload: Dict[str, Any] = {
        # OpenClaw OpenAI-compat: usa "openclaw" (y NO "agent-x")
        "model": "openclaw",
        "messages": messages,
        "temperature": 0.3,
    }

    # Opcional: si defines OPENCLAW_USER en .env, ayuda a mantener sesión estable
    if getattr(settings, "openclaw_user", None):
        payload["user"] = settings.openclaw_user

    return payload

def _headers(session_key: str | None = None, user_id: str | None = None) -> Dict[str, str]:
    h: Dict[str, str] = {}

    # Auth
    tok = settings.openclaw_gateway_token
    if tok:
        h["Authorization"] = f"Bearer {tok}"

    # OpenClaw routing (CLAVE para NO crear sesiones nuevas)
    # Agent ID (ej: "main")
    agent_id = getattr(settings, "openclaw_agent_id", "main")
    h["x-openclaw-agent-id"] = agent_id

    # Session key fija (ej: "agent:main:main")
    # Session key (por usuario/tenant si se pasa)
    sk = session_key or getattr(settings, "openclaw_session_key", None)
    if sk:
        h["x-openclaw-session-key"] = sk

    # User (opcional)
    if user_id:
        h["x-openclaw-user"] = user_id

    return h

async def gateway_chat(user_message: str, system: Optional[str] = None, *, user_id: str | None = None, session_key: str | None = None) -> str:
    timeout = httpx.Timeout(settings.gateway_timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            settings.gateway_url,
            json=_payload(user_message, system),
            headers=_headers(session_key=session_key, user_id=user_id),
        )
        r.raise_for_status()
        data = r.json()

    # OpenAI-style:
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        pass

    # Otros gateways:
    if isinstance(data, dict) and "content" in data and isinstance(data["content"], str):
        return data["content"]

    return str(data)