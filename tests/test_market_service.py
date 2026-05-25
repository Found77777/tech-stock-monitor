import pandas as pd

from app.database import SessionLocal
from app.models import StockSnapshot
from app.services.market_data_service import MarketDataService


class MockSource:
    def get_realtime_quotes(self, symbols):
        return pd.DataFrame([
            {"code": "600001", "name": "某半导体", "price": 10, "pct_change": 1, "change": 0.1, "volume": 1000, "amount": 60000000, "turnover_rate": 2, "pe": 20, "pb": 2, "total_market_cap": 1e9, "float_market_cap": 8e8},
            {"code": "300001", "name": "创业板电子", "price": 10, "pct_change": 1, "change": 0.1, "volume": 1000, "amount": 60000000, "turnover_rate": 2, "pe": 20, "pb": 2, "total_market_cap": 1e9, "float_market_cap": 8e8},
        ])


def test_filter_tech_universe():
    df = MockSource().get_realtime_quotes([])
    filtered = MarketDataService.filter_tech_universe(df, min_amount=1000000)
    assert len(filtered) == 1
    assert filtered.iloc[0]["code"] == "600001"


def test_refresh_insert_flow():
    svc = MarketDataService(source=MockSource())
    db = SessionLocal()
    try:
        result = svc.refresh_snapshot(db)
        assert result["inserted_count"] >= 1
        rows = db.query(StockSnapshot).all()
        assert len(rows) >= 1
    finally:
        db.close()
