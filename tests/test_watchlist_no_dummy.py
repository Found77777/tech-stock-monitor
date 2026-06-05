from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, SessionLocal, engine
from app.models import StockScore
from app.services.analysis_service import AnalysisService


def test_latest_scores_filters_dummy_rows():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(StockScore).filter(StockScore.trade_date == "2099-01-01").delete(synchronize_session=False)
        db.add(StockScore(code="000001", name="N000001", trade_date="2099-01-01", total_score=80, trend_score=50, momentum_score=50, relative_strength_score=50, liquidity_score=50, position_score=50, risk_penalty=0, rank=1, reasons="[]"))
        db.add(StockScore(code="600100", name="同方股份", trade_date="2099-01-01", total_score=77, trend_score=44, momentum_score=61, relative_strength_score=58, liquidity_score=46, position_score=53, risk_penalty=7, rank=2, reasons='["x"]'))
        db.commit()

        rows = AnalysisService().latest_scores(db)
        assert any(x["code"] == "600100" for x in rows)
        assert all(not str(x["name"]).startswith("N000") for x in rows)
    finally:
        db.close()


def test_watchlist_top_no_dummy_and_non_empty_reasons():
    client = TestClient(app)
    resp = client.get("/watchlist/top?limit=20")
    assert resp.status_code == 200
    data = resp.json()
    for row in data:
        assert not str(row.get("name", "")).startswith("N000")
        assert row.get("reasons") is not None
    if len(data) >= 3:
        seq = [float(x.get("total_score", 0) or 0) for x in data[:3]]
        assert not (seq[0] - seq[1] == 1 and seq[1] - seq[2] == 1)
