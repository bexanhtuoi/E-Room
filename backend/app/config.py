from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "E-Room API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    admin_port: int = 9000
    frontend_url: str = "http://localhost:3000"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./e_room.db"
    secret_key: str = "change-me"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
