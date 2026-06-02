import pandas as pd

from app.config import get_settings
from app.data_sources import provider
from app.data_sources.efinance_source import EFinanceDataSource
from app.services.market_data_service import MarketDataService


def test_provider_selects_efinance(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    monkeypatch.setenv("REAL_DATA_SOURCE", "efinance")
    get_settings.cache_clear()
    try:
        assert isinstance(provider.build_data_source(provider.primary_source_name()), EFinanceDataSource)
    finally:
        get_settings.cache_clear()


def test_market_refresh_efinance_does_not_call_akshare(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    monkeypatch.setenv("REAL_DATA_SOURCE", "efinance")
    monkeypatch.setenv("ENABLE_DATA_SOURCE_FALLBACK", "false")
    get_settings.cache_clear()

    class FakeEFinance:
        def get_realtime_quotes(self, symbols):
            return pd.DataFrame([{"code":"600850","name":"电科数字","price":10,"pct_change":1,"change":0.1,"volume":1000,"amount":90000000,"turnover_rate":1,"pe":0,"pb":0,"total_market_cap":0,"float_market_cap":0}])

    def fake_build(name):
        assert name == "efinance"
        return FakeEFinance()

    monkeypatch.setattr("app.services.market_data_service.build_data_source", fake_build)
    svc = MarketDataService()
    df, used = svc._fetch_realtime_with_fallback(["600850"])
    assert used == "efinance"
    assert len(df) == 1
    get_settings.cache_clear()
