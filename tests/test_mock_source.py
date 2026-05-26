from app.data_sources.mock_source import MockDataSource
from app.services.market_data_service import MarketDataService


def test_mock_source_realtime_quotes():
    df = MockDataSource().get_realtime_quotes([])
    assert len(df) >= 30
    required = {"code","name","price","pct_change","change","volume","amount","turnover_rate","pe","pb","total_market_cap","float_market_cap","timestamp"}
    assert required.issubset(df.columns)


def test_mock_source_daily_bars():
    df = MockDataSource().fetch_daily_bars("300308", "2025-01-01", "2025-12-31")
    assert len(df) >= 100
    required = {"code","name","trade_date","open","high","low","close","volume","amount","pct_change","turnover_rate"}
    assert required.issubset(df.columns)


def test_use_mock_data_source_selection():
    svc = MarketDataService(source=MockDataSource())
    df = svc.source.get_realtime_quotes([])
    assert len(df) >= 30
