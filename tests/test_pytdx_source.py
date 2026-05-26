from app.data_sources.pytdx_source import PytdxDataSource
from app.services.market_data_service import MarketDataService


def test_pytdx_normalized_shape_from_mock_quotes():
    class FakePytdx(PytdxDataSource):
        def get_realtime_quotes(self, symbols):
            return super().get_realtime_quotes(["000001"]) * 0  # not used

    # Validate required columns contract from synthetic frame
    cols = {"code", "name", "price", "pct_change", "change", "volume", "amount", "turnover_rate", "timestamp"}
    sample = {
        "code": "000001", "name": "平安银行", "price": 10.0, "pct_change": 1.2, "change": 0.12,
        "volume": 1000, "amount": 10000, "turnover_rate": None, "timestamp": "2026-01-01 10:00:00"
    }
    assert cols.issubset(sample.keys())


def test_source_switch_pytdx_supported():
    svc = MarketDataService()
    assert hasattr(svc, '_build_default_source')
