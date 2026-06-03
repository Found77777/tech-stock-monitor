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
    database_url: str = Field(default=f"sqlite:///{BASE_DIR / 'data' / 'tech_monitor.db'}")

    data_source_provider: str = Field(default="sina")
    real_data_source: str = Field(default="sina")
    history_data_source: str = Field(default="sina")
    tushare_token: str = Field(default="")
    sina_user_agent: str | None = Field(default=None)
    sina_cookie: str | None = Field(default=None)
    min_amount: float = Field(default=50_000_000)
    use_mock_data: bool = Field(default=False)
    enable_data_source_fallback: bool = Field(default=True)

    scheduler_timezone: str = Field(default="Asia/Shanghai")

    # --- AI Agent settings ---
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="https://api.deepseek.com")
    llm_model: str = Field(default="deepseek-chat")
    llm_http_proxy: str = Field(default="")
    agent_news_sources: str = Field(default="sina,eastmoney,cninfo,baidu,rss")
    agent_enabled: bool = Field(default=False)
    capital_flow_source: str = Field(default="efinance")  # eastmoney|efinance|proxy|none
    capital_flow_allow_proxy: bool = Field(default=False)
    capital_flow_top_n: int = Field(default=10)
    capital_flow_verify_top_n: int = Field(default=20)
    capital_flow_sleep_min: float = Field(default=10.0)
    capital_flow_sleep_max: float = Field(default=20.0)
    capital_flow_retry: int = Field(default=3)
    capital_flow_cache_enabled: bool = Field(default=True)
    enable_factor_redundancy_adjustment: bool = Field(default=False)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
