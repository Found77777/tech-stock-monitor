import pandas as pd

from app import models  # noqa
from app.database import Base, SessionLocal, engine
from app.models import DailyBar, StockScore
from app.services.analysis_service import AnalysisService


def test_generate_scores_db_not_nan():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        code = "600100"
        db.query(StockScore).filter(StockScore.code == code).delete(synchronize_session=False)
        db.query(DailyBar).filter(DailyBar.code == code).delete(synchronize_session=False)
        db.commit()
        for i in range(1, 40):
            db.add(DailyBar(code=code, name="测试", trade_date=f"2026-01-{i:02d}", open=10+i*0.1, high=10+i*0.1, low=10+i*0.1, close=10+i*0.1, volume=1000, amount=10000, pct_change=0.1, turnover_rate=1))
        db.commit()
        res = AnalysisService().generate_scores(db)
        assert res["rows"] >= 1
        row = db.query(StockScore).first()
        assert row is not None
        assert row.total_score is not None
        assert row.total_score == row.total_score
    finally:
        db.close()
