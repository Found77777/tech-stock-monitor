from fastapi.testclient import TestClient

from app.api import agent_routes
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import DailyBar, EnhancedStockScore, StockScore


def _reset():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(EnhancedStockScore).delete()
    db.query(StockScore).delete()
    db.query(DailyBar).delete()
    db.commit()
    db.close()
    agent_routes._CAPITAL_FLOW_CACHE.clear()


def _seed_bars(code="600001", trend="up", days=20):
    db = SessionLocal()
    for i in range(days):
        if trend == "up":
            close = 10 + i * 0.2
            amount = 100_000_000 + i * 8_000_000
        elif trend == "weak":
            close = 10 + i * 0.02
            amount = 100_000_000 if i % 2 == 0 else 0
        else:
            close = 14 - i * 0.15
            amount = 250_000_000 + i * 8_000_000
        db.add(DailyBar(code=code, name="测试", trade_date=f"2026-05-{i+1:02d}", open=close-0.1, high=close+0.2, low=close-0.2, close=close, volume=1_000_000, amount=amount, pct_change=0, turnover_rate=None))
    db.commit()
    db.close()


def test_enhanced_stock_score_default_is_not_proxy():
    assert EnhancedStockScore.__table__.c.capital_flow_source.default.arg == "not_verified"


def test_sina_capital_flow_payload_dynamic_and_bounded():
    _reset()
    _seed_bars("600001", "up", days=20)
    _seed_bars("600002", "weak", days=10)

    class S:
        capital_flow_source = "sina"
        capital_flow_allow_proxy = False
        capital_flow_cache_enabled = False

    db = SessionLocal()
    try:
        strong = agent_routes._fetch_capital_flow_with_cache("600001", "2026-05-20", S(), db=db)
        weak = agent_routes._fetch_capital_flow_with_cache("600002", "2026-05-10", S(), db=db)
    finally:
        db.close()

    assert strong["capital_flow_source"] == "sina_volume_amount"
    assert strong["capital_flow_is_real"] is False
    assert strong["capital_flow_is_estimated"] is True
    assert -3 <= strong["capital_flow_adjustment"] <= 3
    assert 0 <= strong["capital_flow_confidence"] <= 80
    assert strong["capital_flow_confidence"] != weak["capital_flow_confidence"]
    assert "Sina量价资金强度" in strong["capital_flow_reason"]


def test_verification_writes_sina_volume_amount_and_no_proxy(monkeypatch):
    _reset()
    _seed_bars("600001", "up", days=20)
    db = SessionLocal()
    db.add(StockScore(code="600001", name="测试", trade_date="2026-05-20", total_score=70, trend_score=70, momentum_score=70, relative_strength_score=70, liquidity_score=70, position_score=70, risk_penalty=0, rank=1, reasons="[]"))
    db.commit()
    db.close()

    monkeypatch.setenv("CAPITAL_FLOW_SOURCE", "sina")
    monkeypatch.setenv("CAPITAL_FLOW_ALLOW_PROXY", "false")
    from app.config import get_settings
    get_settings.cache_clear()

    client = TestClient(app)
    resp = client.post("/verification/capital-flow-top?top_n=1&force_refresh=true")
    assert resp.status_code == 200
    row = resp.json()["results"][0]
    assert row["capital_flow_source"] == "sina_volume_amount"
    assert "proxy" not in row["capital_flow_source"]

    top = client.get("/watchlist/enhanced-top?limit=1")
    assert top.status_code == 200
    assert top.json()[0]["capital_flow_source"] == "sina_volume_amount"
    assert top.json()[0]["capital_flow_is_estimated"] is True
