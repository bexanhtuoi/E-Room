import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def livekit_profile_env(suffix: str, default: str = "") -> str:
    # Doc cum local/cloud theo LIVEKIT_MODE. Tra ve default khi MODE khong hop le.
    mode = os.getenv("LIVEKIT_MODE", "").strip().lower()

    if mode not in ("local", "cloud"):
        return default

    return os.getenv(f"LIVEKIT_{mode.upper()}_{suffix}", default)


class Settings:
    # NOTE: thu tu section giong 3 file env (.env, .env.docker, .env.example):
    # App, Auth, Database, Redis, LLM, Embedding, Reranker, STT, Qdrant,
    # Search, LiveKit, MinIO, Stripe, Heartbeat, Logging.

    # ─── App ────────────────────────────────────────
    app_name: str = os.getenv("APP_NAME", "E-Room API")
    app_description: str = os.getenv("APP_DESCRIPTION", "Realtime English speaking rooms with AI support")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", 8000))
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # ─── Auth ───────────────────────────────────────
    secret_key: str = os.getenv("SECRET_KEY", "secret")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expires_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 120))
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    )
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    rate_limit_login_attempts: int = int(os.getenv("RATE_LIMIT_LOGIN_ATTEMPTS", 20))
    rate_limit_login_window_seconds: int = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", 300))
    rate_limit_register_attempts: int = int(os.getenv("RATE_LIMIT_REGISTER_ATTEMPTS", 10))
    rate_limit_register_window_seconds: int = int(os.getenv("RATE_LIMIT_REGISTER_WINDOW_SECONDS", 3600))

    # ─── Database ───────────────────────────────────
    db_user: str = os.getenv("DB_USER", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", 4000))
    db_name: str = os.getenv("DB_NAME", "ERoom")
    database_url_override: str = os.getenv("DATABASE_URL", "")

    # ─── Redis ──────────────────────────────────────
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ─── LLM ────────────────────────────────────────
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    llm_model: str = os.getenv("LLM_MODEL", "google/gemma-4-e2b")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    ai_timeout_seconds: int = int(os.getenv("AI_TIMEOUT_SECONDS", 900))
    # Soft < hard de worker kip dang cau xin loi truoc khi bi kill.
    # Mac dinh kem hard 60s (toi thieu 60s); khong bao gio vuot qua hard.
    ai_soft_timeout_seconds: int = min(
        int(os.getenv("AI_SOFT_TIMEOUT_SECONDS", max(60, ai_timeout_seconds - 60))),
        ai_timeout_seconds,
    )
    llm_call_timeout_seconds: int = int(os.getenv("LLM_CALL_TIMEOUT_SECONDS", 120))
    ai_queue_name: str = os.getenv("AI_QUEUE_NAME", "ai")
    ai_observer_queue_name: str = os.getenv("AI_OBSERVER_QUEUE_NAME", "ai_observer")
    ai_transcriber_queue_name: str = os.getenv("AI_TRANSCRIBER_QUEUE_NAME", "ai_transcriber")
    # 0 = khong gioi han boi Redis (dua hoan toan vao concurrency cua worker)
    # > 0 = gioi han N luong chay song song tren TOAN HE THONG (du co nhieu server worker)
    ai_max_concurrency: int = int(os.getenv("AI_MAX_CONCURRENCY", 0))

    # ─── Embedding ──────────────────────────────────
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "")
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")

    # ─── Reranker ───────────────────────────────────
    reranker_model: str = os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-0.6B")
    reranker_base_url: str = os.getenv("RERANKER_BASE_URL", "")
    reranker_api_key: str = os.getenv("RERANKER_API_KEY", "")

    # ─── STT (whisper-server rieng, OpenAI-compatible) ────────────────────
    # auto: whisper host (:8001) song thi dung, chet thi fallback local cu.
    stt_provider: str = os.getenv("STT_PROVIDER", "auto")  # auto | whisper_server | faster_whisper | local | openai | groq | cloud
    stt_model_size: str = os.getenv("STT_MODEL_SIZE", "small")
    stt_device: str = os.getenv("STT_DEVICE", "cpu")
    stt_compute_type: str = os.getenv("STT_COMPUTE_TYPE", "int8")
    stt_cpu_threads: int = int(os.getenv("STT_CPU_THREADS", 2))
    stt_beam_size: int = int(os.getenv("STT_BEAM_SIZE", 3))
    # Timeout cho health-check whisper host (auto mode). Ngan de chet nhanh fallback local.
    stt_server_alive_timeout: float = float(os.getenv("STT_SERVER_ALIVE_TIMEOUT", 3.0))
    stt_server_alive_ttl: float = float(os.getenv("STT_SERVER_ALIVE_TTL", 60.0))
    stt_language: str = os.getenv("STT_LANGUAGE", "en")  # en | vi | auto
    stt_cloud_api_key: str = os.getenv("STT_CLOUD_API_KEY", "")
    stt_cloud_base_url: str = os.getenv("STT_CLOUD_BASE_URL", "https://api.openai.com/v1")
    stt_cloud_model: str = os.getenv("STT_CLOUD_MODEL", "whisper-1")
    # faster-whisper-server riêng (OpenAI-compatible, chạy :8001 để tránh đụng api :8000)
    stt_server_base_url: str = os.getenv("STT_SERVER_BASE_URL", "http://localhost:8001/v1")
    stt_server_api_key: str = os.getenv("STT_SERVER_API_KEY", "cant-be-empty")
    stt_server_model: str = os.getenv("STT_SERVER_MODEL", "mobiuslabsgmbh/faster-whisper-large-v3-turbo")
    stt_server_timeout: float = float(os.getenv("STT_SERVER_TIMEOUT", 30.0))
    stt_local_enabled: bool = os.getenv("STT_LOCAL_ENABLED", "true").lower() in ("true", "1", "yes")
    stt_vad_silence_seconds: float = float(os.getenv("STT_VAD_SILENCE_SECONDS", 2.0))
    stt_vad_min_speech_seconds: float = float(os.getenv("STT_VAD_MIN_SPEECH_SECONDS", 0.5))
    stt_vad_max_speech_seconds: float = float(os.getenv("STT_VAD_MAX_SPEECH_SECONDS", 20.0))
    stt_vad_energy_threshold: float = float(os.getenv("STT_VAD_ENERGY_THRESHOLD", 0.01))
    stt_vad_threshold: float = float(os.getenv("STT_VAD_THRESHOLD", 0.5))

    # ─── TTS (Kokoro server rieng, OpenAI-compatible, :8002) ───────────────
    tts_base_url: str = os.getenv("TTS_BASE_URL", "http://localhost:8002/v1")
    tts_model: str = os.getenv("TTS_MODEL", "kokoro")
    tts_voice: str = os.getenv("TTS_VOICE", "af_heart")
    tts_speed: float = float(os.getenv("TTS_SPEED", 0.9))
    tts_timeout: float = float(os.getenv("TTS_TIMEOUT", 30.0))

    # ─── Pronun scorer (demo/pronun-app, :8005, chay tren MAY AI) ─────────
    # De trong = dung heuristic noi bo. Co URL = goi scorer that (wav2vec2 + GOP).
    # May AI chay `docker compose -f docker-compose.stt.yml up -d` (service `pronun`).
    pronun_base_url: str = os.getenv("PRONUN_BASE_URL", "")
    pronun_timeout: float = float(os.getenv("PRONUN_TIMEOUT", 300.0))
    # May host web yeu (3-4 nguoi cham cung luc): serialize inference local
    # de khong spike RAM/VRAM. 1 = tuan tu hoan toan (khuyen nghi).
    scoring_max_parallel: int = max(1, int(os.getenv("SCORING_MAX_PARALLEL", "1") or 1))

    # ─── Scorer local (ruot scorer port vao backend: wav2vec2 + phoneme GOP) ──
    # May chay backend gánh compute. Model tai 1 lan vao HF cache.
    wav2vec_model_id: str = os.getenv("WAV2VEC_MODEL_ID", "facebook/wav2vec2-base-960h")
    phoneme_model_id: str = os.getenv("PHONEME_MODEL_ID", "facebook/wav2vec2-xlsr-53-espeak-cv-ft")
    # Chon backend cham diem: local | remote | remote-strict.
    # local = worker tu cham (mac dinh, khong doi hanh vi).
    # remote = POST sang server scorer (EC2), loi tu rot ve local.
    # remote-strict = chi dung server ngoai, loi thi bo qua cau do.
    # (gia tri cu lambda/lambda-strict van chay, tu map sang remote.)
    scorer_backend: str = os.getenv("SCORER_BACKEND", "local")
    scorer_url: str = os.getenv("SCORER_URL", "") or os.getenv("SCORER_LAMBDA_URL", "")
    scorer_api_key: str = os.getenv("SCORER_API_KEY", "")
    scorer_timeout: float = float(os.getenv("SCORER_TIMEOUT", 300.0))

    # ─── LLM feedback (LLM local qua get_llm, chi doc ScoringReport) ───────
    # Khong can key rieng — dung chung LLM_BASE_URL/LLM_MODEL.

    # ─── Speech logs (per-user transcript files cho summary + pronunciation) ─
    speech_log_dir: str = os.getenv("SPEECH_LOG_DIR", "log/speech")
    speech_log_save_audio: bool = os.getenv("SPEECH_LOG_SAVE_AUDIO", "true").lower() in ("true", "1", "yes")

    # ─── Raw attempt recording (song song VAD, ghi TOÀN BỘ audio liên tục) ──
    speech_raw_enabled: bool = os.getenv("SPEECH_RAW_ENABLED", "true").lower() in ("true", "1", "yes")
    speech_raw_end_silence_seconds: float = float(os.getenv("SPEECH_RAW_END_SILENCE_SECONDS", 8.0))
    speech_raw_max_attempt_seconds: float = float(os.getenv("SPEECH_RAW_MAX_ATTEMPT_SECONDS", 300.0))
    speech_raw_flush_bytes: int = int(os.getenv("SPEECH_RAW_FLUSH_BYTES", 65536))
    otel_enabled: bool = os.getenv("OTEL_ENABLED", "false").lower() in ("true", "1", "yes")
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "eroom")
    otel_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")

    # ─── Qdrant ─────────────────────────────────────
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", 6333))
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "embedded_documents")

    # ─── Search ─────────────────────────────────────
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    brave_search_api_key: str = os.getenv("BRAVE_SEARCH_API_KEY", "")

    # ─── Stripe ─────────────────────────────────────
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # ─── LiveKit ────────────────────────────────────
    # Chon cum bang LIVEKIT_MODE=local|cloud (xem backend/.env.docker).
    livekit_mode: str = os.getenv("LIVEKIT_MODE", "").strip().lower()
    livekit_url: str = livekit_profile_env("URL", "ws://localhost:7880")
    livekit_api_key: str = livekit_profile_env("API_KEY")
    livekit_api_secret: str = livekit_profile_env("API_SECRET")

    # ─── MinIO ──────────────────────────────────────
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "eroom")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

    # ─── Heartbeat ──────────────────────────────────
    heartbeat_interval_seconds: int = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", 45))
    # Phong trong (0 nguoi) qua lau thi ENDED cho gon list (mac dinh 24h)
    room_empty_end_seconds: int = int(os.getenv("ROOM_EMPTY_END_SECONDS", 86400))

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

if settings.secret_key == "secret" and settings.app_env != "development":
    raise RuntimeError("SECRET_KEY must be set in non-development environments")
