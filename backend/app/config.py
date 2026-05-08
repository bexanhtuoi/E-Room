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

    database_url: str = "sqlite:///./e_room.db"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expires_minutes: int = 15
    refresh_token_expires_days: int = 7

    log_level: str = "INFO"
    log_file: str = "log/app.log"

    static_dir: str = "static"
    avatar_dir: str = "static/avatars"
    upload_dir: str = "static/uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
