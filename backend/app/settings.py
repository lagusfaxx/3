from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # <- evita que crashee si hay vars extra en .env
    )

    gateway_url: str = "http://127.0.0.1:18789/v1/chat/completions"
    use_gateway: bool = False
    gateway_timeout: int = 60

    # Token opcional para auth del Gateway
    openclaw_gateway_token: str | None = None

    # Mantener sesión / agente (para que no cree chat nuevo)
    openclaw_agent_id: str = "main"
    openclaw_session_key: str | None = None
    openclaw_user: str | None = None

    # Persistencia local (demo)
    db_path: str = "backend/app/data/app.db"
    downloads_dir: str | None = None

settings = Settings()
