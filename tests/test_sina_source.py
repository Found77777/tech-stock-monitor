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
    # just validate selection object exists and supports interface
    assert hasattr(svc.source, 'get_realtime_quotes')
