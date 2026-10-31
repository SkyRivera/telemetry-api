from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgre5"
    POSTGRES_DB: str = "telemetry_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 40
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 3600

    # FastAPI
    APP_NAME: str = "Telemetry API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "API for forest IoT monitoring"
    SECRET_KEY: str = "your_secret_key_here_min_32_chars"
    API_KEY_IOT: str = "your_api_key_for_iot_devices"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60  # segundos

    # Command Timeout
    COMMAND_TIMEOUT_SECONDS: int = 30
    COMMAND_POLL_INTERVAL: int = 5  # segundos

    # Telemetry
    MAX_TELEMETRY_PER_REQUEST: int = 1000
    TELEMETRY_RETENTION_DAYS: int = 30

    @property
    def DATABASE_URL(self) -> str:
        """Genera la URL de conexión a PostgreSQL"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_SYNC_URL(self) -> str:
        """URL para SQLAlchemy sincrónico"""
        return self.DATABASE_URL

    @property
    def DATABASE_ASYNC_URL(self) -> str:
        """URL para SQLAlchemy asíncrono"""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Singleton de configuración con cache"""
    return Settings()
