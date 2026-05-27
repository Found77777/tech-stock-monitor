from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import EnhancedStockScore, StockScore


def _seed_base_scores(n=25):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(EnhancedStockScore).delete()
    db.query(StockScore).delete()
    for i in range(n):
        code = f"{600000+i}"
        db.add(StockScore(code=code, name=f"S{code}", trade_date="2026-05-27", total_score=100-i, trend_score=50, momentum_score=50, relative_strength_score=50, liquidity_score=50, position_score=50, risk_penalty=0, rank=i+1, reasons='["r"]'))
    db.commit()
    db.close()


def test_capital_flow_top_only_top20():
    _seed_base_scores(25)
    client = TestClient(app)
    r = client.post('/verification/capital-flow-top?top_n=20')
    assert r.status_code == 200
    data = r.json()
    assert data['verified_count'] == 20
    assert len(data['results']) == 20


def test_capital_flow_top_cap_30():
    _seed_base_scores(40)
    client = TestClient(app)
    r = client.post('/verification/capital-flow-top?top_n=999')
    assert r.status_code == 200
    assert len(r.json()['results']) <= 30


def test_enhanced_top_fallback_base_watchlist():
    db = SessionLocal()
    db.query(EnhancedStockScore).delete()
    db.commit()
    db.close()
    client = TestClient(app)
    r = client.get('/watchlist/enhanced-top?limit=5')
    assert r.status_code == 200
    assert isinstance(r.json(), list)
