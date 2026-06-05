from app.config import get_settings


def test_settings_loaded():
    settings = get_settings()
    assert settings.app_name
    assert settings.database_url.startswith("sqlite")


def test_enable_factor_redundancy_adjustment_env_mapping(monkeypatch):
    monkeypatch.setenv("ENABLE_FACTOR_REDUNDANCY_ADJUSTMENT", "true")
    from app.config import Settings

    settings = Settings()
    assert settings.enable_factor_redundancy_adjustment is True


def test_llm_http_proxy_mapping(monkeypatch):
    monkeypatch.setenv("LLM_HTTP_PROXY", "http://127.0.0.1:7890")
    from app.config import Settings

    settings = Settings()
    assert settings.llm_http_proxy == "http://127.0.0.1:7890"


def test_agent_news_sources_default_include_resilient_sources():
    from app.config import Settings

    settings = Settings(_env_file=None)
    sources = {x.strip() for x in settings.agent_news_sources.split(",")}
    assert {"sina", "eastmoney", "cninfo", "baidu", "rss"}.issubset(sources)


def test_data_source_and_capital_flow_defaults_are_safe(monkeypatch):
    monkeypatch.delenv("REAL_DATA_SOURCE", raising=False)
    monkeypatch.delenv("HISTORY_DATA_SOURCE", raising=False)
    monkeypatch.delenv("CAPITAL_FLOW_SOURCE", raising=False)
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.real_data_source == "sina"
    assert settings.history_data_source == "sina"
    assert settings.enable_data_source_fallback is True
    assert settings.capital_flow_source == "sina"
    assert settings.capital_flow_allow_proxy is False


def test_llm_defaults_use_deepseek_base():
    from app.config import Settings

    settings = Settings(_env_file=None)
    assert settings.llm_base_url == "https://api.deepseek.com"
    assert settings.llm_model == "deepseek-chat"
