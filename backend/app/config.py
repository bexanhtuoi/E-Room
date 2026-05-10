from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "E-Room API"
    app_description: str = "Realtime English speaking rooms with AI support"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    admin_host: str = "0.0.0.0"
    admin_port: int = 9000

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "mysql+pymysql://43pCkc13g2qBjEF.root:lD0uSieZCD23ERII@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/ERoom"
    database_url_sync: str = "mysql+pymysql://43pCkc13g2qBjEF.root:lD0uSieZCD23ERII@gateway01.ap-southeast-1.prod.alicloud.tidbcloud.com:4000/ERoom"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 15
    refresh_token_expires_days: int = 7

    llm_base_url: str = "http://localhost:20128/v1"
    llm_model: str = "ds2api/deepseek-v4-flash-nothinking"
    llm_api_key: str = "sk-a25797aebad34b33-cfw0o9-eab4bc80"

    log_level: str = "INFO"
    log_file: str = "log/app.log"

    static_dir: str = "static"
    avatar_dir: str = "static/avatars"
    upload_dir: str = "static/uploads"

    livekit_url: str = "ws://localhost:7880"
    livekit_api_key: str = "devkey"
    livekit_api_secret: str = "secret"
    turn_server_url: str = "turn:localhost:3478"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "e-room-rag-docs"
    minio_secure: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
