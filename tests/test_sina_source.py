from datetime import date

from app.data_sources import sina_source as sina_module
from app.data_sources.sina_source import SinaDataSource
from app.services.market_data_service import MarketDataService


def test_sina_normalize_fields():
    txt = 'var hq_str_sz000001="平安银行,10.00,9.90,10.10,10.20,9.80,0,0,100000,100000000,0,0,0,0,0,0,0,0,0,0,2026-05-25,15:00:00,00";\n'
    df = SinaDataSource().normalize_sina_text(txt)
    assert len(df) == 1
    required = {"code","name","price","pct_change","change","volume","amount","turnover_rate","timestamp"}
    assert required.issubset(df.columns)


def test_source_switch_mock_fallback():
    svc = MarketDataService()
    assert hasattr(svc.source, 'get_realtime_quotes')


def test_sina_advanced_kline_maps_ohlcv_amount_and_null_turnover(monkeypatch):
    s = SinaDataSource()
    payload = '[{"day":"2026-05-20","open":"10.0","high":"11.0","low":"9.0","close":"10.5","volume":"10000"}]'
    captured = {}

    class R:
        text = payload
        def raise_for_status(self):
            return None

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return R()

    monkeypatch.setattr(sina_module.requests, "get", fake_get)
    df = s.fetch_daily_bars("600000", "2026-05-01", "2026-05-30")
    row = df.iloc[0]
    assert captured["params"]["symbol"] == "sh600000"
    assert captured["params"]["scale"] == 240
    assert captured["headers"]["User-Agent"] == "Mozilla/5.0"
    assert row["trade_date"] == "2026-05-20"
    assert row["open"] == 10.0
    assert row["high"] == 11.0
    assert row["low"] == 9.0
    assert row["close"] == 10.5
    assert row["volume_raw"] == 10000.0
    assert row["volume"] == 100.0  # daily_bars.volume remains in hands
    assert row["amount"] == ((10.0 + 11.0 + 9.0 + 10.5) / 4) * 10000.0
    assert bool(row["amount_estimated"]) is True
    assert row["turnover_rate"] is None
    assert bool(row["turnover_rate_estimated"]) is False


def test_sina_get_history_defaults_end_date_to_today_without_fixed_date(monkeypatch):
    class FakeDate(date):
        @classmethod
        def today(cls):
            return cls(2030, 1, 2)

    payload = '[{"day":"2030-01-02","open":"10","high":"10","low":"10","close":"10","volume":"100"}]'
    captured = {}

    class R:
        text = payload
        def raise_for_status(self):
            return None

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["params"] = params
        return R()

    monkeypatch.setattr(sina_module, "date", FakeDate)
    monkeypatch.setattr(sina_module.requests, "get", fake_get)
    df = SinaDataSource().get_history("000001", days=1)
    assert captured["params"]["symbol"] == "sz000001"
    assert captured["params"]["datalen"] == 1
    assert list(df["trade_date"]) == ["2030-01-02"]


def test_sina_turnover_uses_float_shares_only_when_supplied():
    rows = [{"day": "2026-05-20", "open": "10", "high": "10", "low": "10", "close": "10", "volume": "1000"}]
    s = SinaDataSource()
    without_float = s.normalize_history_rows(rows, "600000")
    with_float = s.normalize_history_rows(rows, "600000", float_shares=10_000)
    assert without_float.iloc[0]["turnover_rate"] is None
    assert with_float.iloc[0]["turnover_rate"] == 10.0
