from __future__ import annotations

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── App ────────────────────────────────────────
    app_name: str = "E-Room API"
    app_description: str = "Realtime English speaking rooms with AI support"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # ─── Database: TiDB ───────────────────────────────
    db_user: str = "root"
    db_password: str = ""
    db_host: str = "localhost"
    db_port: int = 4000
    db_name: str = "ERoom"
    database_url: str = ""
    database_url_sync: str = ""

    # ─── Redis ──────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ─── Auth / JWT ─────────────────────────────────
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 15
    refresh_token_expires_days: int = 7

    # ─── AI / LLM ──────────────────────────────────
    llm_base_url: str = "http://127.0.0.1:1234/v1"
    llm_model: str = "google/gemma-4-e2b"
    llm_api_key: str = "sk-lm-tdSctD3c:eRRhBKL0vRtCMq14EeUr"
    nomic_api_key: str = ""
    brave_search_api_key: str = ""

    # ─── TTS (ElevenLabs) ──────────────────────────
    elevenlabs_api_key: str = ""

    # ─── Stripe (Subscription) ─────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # ─── LiveKit (WebRTC) ──────────────────────────
    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # ─── TURN / coTURN ─────────────────────────────
    turn_server_url: str = "turn:localhost:3478"

    # ─── MinIO (Object Storage) ─────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "ERoom"
    minio_secure: bool = False

    # ─── Heartbeat ──────────────────────────────────
    heartbeat_interval_seconds: int = 45

    # ─── Logging ────────────────────────────────────
    log_level: str = "INFO"
    log_file: str = "log/app.log"

    # ─── Computed ──────────────────────────────────
    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        if not self.db_host:
            return ""
        pw = quote_plus(self.db_password) if self.db_password else ""
        return (
            f"mysql+pymysql://{self.db_user}:{pw}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def db_url_sync(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return self.db_url

    @property
    def db_connect_args(self) -> dict:
        url = self.db_url_sync or self.db_url
        if not url.startswith("mysql"):
            return {}
        if self.db_host in ("localhost", "127.0.0.1", "::1"):
            return {}
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}


settings = Settings()
