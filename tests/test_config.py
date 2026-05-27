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
