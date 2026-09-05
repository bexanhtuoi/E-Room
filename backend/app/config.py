import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ─── App ────────────────────────────────────────
    app_name: str = os.getenv("APP_NAME", "E-Room API")
    app_description: str = os.getenv("APP_DESCRIPTION", "Realtime English speaking rooms with AI support")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", 8000))
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ─── Database: TiDB ───────────────────────────────
    db_user: str = os.getenv("DB_USER", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", 4000))
    db_name: str = os.getenv("DB_NAME", "ERoom")
    database_url_override: str = os.getenv("DATABASE_URL", "")

    # ─── Redis ──────────────────────────────────────
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ─── Auth / JWT ─────────────────────────────────
    secret_key: str = os.getenv("SECRET_KEY", "secret")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expires_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))

    # ─── Google OAuth (Login with Google) ─────────────
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    )

    # ─── AI / LLM / RAG ───────────────────────────
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    llm_model: str = os.getenv("LLM_MODEL", "google/gemma-4-e2b")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "")
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", 300))
    # Phong trong (0 nguoi) qua lau thi ENDED cho gon list (mac dinh 24h)
    room_empty_end_seconds: int = int(os.getenv("ROOM_EMPTY_END_SECONDS", 86400))
    ai_queue_name: str = os.getenv("AI_QUEUE_NAME", "ai")
    ai_observer_queue_name: str = os.getenv("AI_OBSERVER_QUEUE_NAME", "ai_observer")
    ai_transcriber_queue_name: str = os.getenv("AI_TRANSCRIBER_QUEUE_NAME", "ai_transcriber")

    # ─── Speech To Text (STT) ─────────────────────
    stt_provider: str = os.getenv("STT_PROVIDER", "faster_whisper")  # faster_whisper | openai | groq | custom_api
    stt_model_size: str = os.getenv("STT_MODEL_SIZE", "base.en")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")
    stt_cloud_api_key: str = os.getenv("STT_CLOUD_API_KEY", "")
    stt_cloud_base_url: str = os.getenv("STT_CLOUD_BASE_URL", "https://api.openai.com/v1")
    stt_cloud_model: str = os.getenv("STT_CLOUD_MODEL", "whisper-1")
    stt_vad_silence_seconds: float = float(os.getenv("STT_VAD_SILENCE_SECONDS", 2.0))
    stt_vad_min_speech_seconds: float = float(os.getenv("STT_VAD_MIN_SPEECH_SECONDS", 0.5))
    stt_vad_max_speech_seconds: float = float(os.getenv("STT_VAD_MAX_SPEECH_SECONDS", 20.0))
    stt_vad_energy_threshold: float = float(os.getenv("STT_VAD_ENERGY_THRESHOLD", 0.01))
    # 0 = khong gioi han boi Redis (dua hoan toan vao concurrency cua worker)
    # > 0 = gioi han N luong chay song song tren TOAN HE THONG (du co nhieu server worker)
    ai_max_concurrency: int = int(os.getenv("AI_MAX_CONCURRENCY", 0))
    reranker_model: str = os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-0.6B")
    reranker_base_url: str = os.getenv("RERANKER_BASE_URL", "")
    reranker_api_key: str = os.getenv("RERANKER_API_KEY", "")
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", 6333))
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "embedded_documents")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    brave_search_api_key: str = os.getenv("BRAVE_SEARCH_API_KEY", "")

    # ─── Stripe (Subscription) ─────────────────────
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # ─── LiveKit (WebRTC) ──────────────────────────
    livekit_url: str = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    livekit_api_key: str = os.getenv("LIVEKIT_API_KEY", "")
    livekit_api_secret: str = os.getenv("LIVEKIT_API_SECRET", "")

    # ─── MinIO (Object Storage) ─────────────────────
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "eroom")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

    # ─── Heartbeat ──────────────────────────────────
    heartbeat_interval_seconds: int = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", 45))

    # ─── Logging ────────────────────────────────────
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "log/app.log")

    # ─── Computed ──────────────────────────────────
    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        pw = quote_plus(self.db_password) if self.db_password else ""
        return f"mysql+pymysql://{self.db_user}:{pw}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def db_connect_args(self) -> dict:
        if not self.database_url.startswith("mysql"):
            return {}
        if self.db_host in ("localhost", "127.0.0.1", "::1"):
            return {}
        import ssl

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return {"ssl": ctx}


settings = Settings()
