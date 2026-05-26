import os
import pandas as pd

from app import models  # noqa
from app.config import get_settings
from app.data_sources.sina_source import SinaDataSource
from app.database import Base, SessionLocal, engine
from app.models import DailyBar, StockSnapshot
from app.services.history_data_service import HistoryDataService


def test_history_source_manual_injection():
    class X: ...
    svc = HistoryDataService(source=X())
    assert svc.source is not None


def test_history_source_has_name():
    os.environ['USE_MOCK_DATA'] = 'true'
    get_settings.cache_clear()
    svc = HistoryDataService()
    _, name = svc._resolve_source()
    assert name == 'mock'


def test_history_source_selects_sina_from_env():
    os.environ['USE_MOCK_DATA'] = 'false'
    os.environ['REAL_DATA_SOURCE'] = 'sina'
    get_settings.cache_clear()
    svc = HistoryDataService()
    source, name = svc._resolve_source()
    assert name == 'sina'
    assert isinstance(source, SinaDataSource)


def test_history_row_nested_guard():
    svc = HistoryDataService(source=object())
    assert svc._row_has_nested({"a": 1, "b": "x"}) is False
    assert svc._row_has_nested({"a": {"x": 1}}) is True


def test_fill_name_before_insert_when_none():
    Base.metadata.create_all(bind=engine)

    class FakeSource:
        def fetch_daily_bars(self, code: str, start_date: str, end_date: str):
            return pd.DataFrame([
                {"code": code, "name": None, "trade_date": "2026-05-20", "open": 10.0, "high": 10.2, "low": 9.8, "close": 10.1, "volume": 1000.0, "amount": 10000.0, "pct_change": 1.0, "turnover_rate": None}
            ])

    db = SessionLocal()
    try:
        db.add(StockSnapshot(code="600100", name="测试名称", price=10, pct_change=0, change=0, volume=0, amount=0, turnover_rate=0, pe=0, pb=0, total_market_cap=0, float_market_cap=0, timestamp="2026-05-20 10:00:00"))
        db.commit()

        svc = HistoryDataService(source=FakeSource())
        result = svc.refresh(db, days=5)
        assert result["inserted"] >= 1
        row = db.query(DailyBar).filter_by(code="600100", trade_date="2026-05-20").first()
        assert row is not None
        assert row.name is not None
        assert row.name == "测试名称"
    finally:
        db.close()
