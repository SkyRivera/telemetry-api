from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Aplicación
    app_name: str = "telemetry-api"
    debug: bool = False

    # Base de datos
    database_url: str = "postgresql+asyncpg://postgres:postgre5@localhost:5432/telemetry_db"
    db_echo: bool = False

    # Seguridad
    api_key_esp32: str = "esp32-secret-key-change-me"
    api_key_api_b: str = "api-b-secret-key-change-me"

    # Solicitudes de lectura
    read_request_timeout_seconds: int = 300  # 5 minutos

    # Rate limiting
    rate_limit_default: str = "100/minute"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
