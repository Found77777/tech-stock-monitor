"""Application configuration management."""
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    """Centralized application settings loaded from environment variables."""

    app_name: str = Field(default="A-Share Tech Stock Monitor")
    app_env: str = Field(default="dev")
    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)

    database_url: str = Field(default=f"sqlite:///{BASE_DIR / 'data' / 'tech_monitor.db'}")

    data_source_provider: str = Field(default="akshare")
    real_data_source: str = Field(default="akshare")
    tushare_token: str = Field(default="")
    min_amount: float = Field(default=30_000_000)
    use_mock_data: bool = Field(default=False)

    scheduler_timezone: str = Field(default="Asia/Shanghai")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
