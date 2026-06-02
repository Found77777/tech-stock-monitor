import pandas as pd

from app import models  # noqa
from app.database import Base, SessionLocal, engine
from app.services.market_data_service import MarketDataService


class FakeSource:
    def get_realtime_quotes(self, symbols):
        return pd.DataFrame([
            {"code":"600100","name":"科技标的","price":10,"pct_change":1,"change":0.1,"volume":1000,"amount":90000000,"turnover_rate":1.2,"pe":None,"pb":None,"total_market_cap":None,"float_market_cap":None,"timestamp":""}
        ])


def test_market_refresh_has_universe_count():
    Base.metadata.create_all(bind=engine)
    svc = MarketDataService(source=FakeSource())
    db = SessionLocal()
    try:
        r = svc.refresh_snapshot(db)
        assert 'universe_count' in r
        assert 'raw_count' in r
        assert 'filtered_count' in r
    finally:
        db.close()
