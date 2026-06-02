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


def test_ai_fallback_keeps_ai_adjustment_zero(monkeypatch):
    _seed_base_scores(5)
    db = SessionLocal()
    # seed layer2 style enhanced row
    db.add(EnhancedStockScore(
        code="600000", name="S600000", trade_date="2026-05-27",
        base_rank=1, base_total_score=90, capital_flow_score=60, capital_flow_source="proxy",
        capital_flow_adjustment=-4, ai_adjustment=0, enhanced_score=86, enhanced_rank=1,
        reasons="flow", ai_adjusted_score=86, ai_sentiment_score=0, ai_confidence=0, ai_reasons='["未抓取到有效新闻，暂不调整评分"]',
        original_rank=1, new_rank=1
    ))
    db.commit()
    db.close()

    from app.api import agent_routes
    class DummyAgent:
        def __init__(self, settings): pass
        async def analyze_stocks(self, stock_codes): return []
        async def market_overview(self): return {"market_sentiment": 0, "tech_sector_sentiment": 0}
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyAgent)

    client = TestClient(app)
    r = client.post("/agent/analyze-top", json={"top_n": 1, "rerank": True})
    assert r.status_code == 200
    row = r.json()["items"][0]
    assert row["ai_adjustment"] == 0
    assert row["ai_adjusted_score"] == row["original_score"] + row["capital_flow_adjustment"]
    assert any("未抓取到有效新闻" in x for x in row["ai_reasons"])
