from app import models  # noqa: F401
from app.database import Base, SessionLocal, engine
from app.models import DailyBar, StockScore
from app.services.analysis_service import AnalysisService


def test_score_row_missing_name_filled_from_universe_or_code():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        code = "600100"
        db.query(StockScore).filter(StockScore.code == code).delete(synchronize_session=False)
        db.query(DailyBar).filter(DailyBar.code == code).delete(synchronize_session=False)
        db.commit()
        # name deliberately equals code (treated as missing semantic name)
        for i in range(1, 40):
            db.add(
                DailyBar(
                    code=code,
                    name=code,
                    trade_date=f"2026-02-{i:02d}",
                    open=10 + i * 0.1,
                    high=10 + i * 0.1,
                    low=10 + i * 0.1,
                    close=10 + i * 0.1,
                    volume=1000,
                    amount=10000,
                    pct_change=0.1,
                    turnover_rate=1,
                )
            )
        db.commit()

        res = AnalysisService().generate_scores(db)
        assert res["rows"] >= 1
        latest = AnalysisService().latest_scores(db)
        target = next((x for x in latest if x["code"] == code), None)
        assert target is not None
        assert target["name"] is not None
        assert str(target["name"]).strip() != ""
    finally:
        db.close()


def test_watchlist_top_name_not_empty():
    db = SessionLocal()
    try:
        latest = AnalysisService().latest_scores(db)
        if not latest:
            return
        for item in latest[:20]:
            assert item["name"] is not None
            assert str(item["name"]).strip() != ""
    finally:
        db.close()
