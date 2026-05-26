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


def test_sina_daily_rows_flattened_values_not_nested():
    s = SinaDataSource()
    fake = {
        "data": {
            "sh600000": {
                "qfqday": [
                    ["2026-05-20", "10.0", "10.2", "10.3", "9.9", "1000", "10000"],
                    ["2026-05-21", "10.2", "10.1", "10.4", "10.0", "900", {"bad": 1}],
                ],
                "meta": {"x": 1},
            }
        }
    }

    class R:
        def raise_for_status(self):
            return None
        def json(self):
            return fake

    import requests
    old = requests.get
    requests.get = lambda *args, **kwargs: R()
    try:
        df = s.fetch_daily_bars("600000", "2026-05-01", "2026-05-30")
    finally:
        requests.get = old

    assert len(df) >= 1
    for _, row in df.iterrows():
        for v in row.to_dict().values():
            assert not isinstance(v, (dict, list, tuple))
