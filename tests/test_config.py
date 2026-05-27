from app.config import get_settings


def test_settings_loaded():
    settings = get_settings()
    assert settings.app_name
    assert settings.database_url.startswith("sqlite")
