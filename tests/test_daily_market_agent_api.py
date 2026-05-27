from fastapi.testclient import TestClient

from app.api import agent_routes
from app.database import Base, engine
from app.main import app


class DummyDailyAgent:
    def __init__(self, settings):
        pass

    async def run(self, date=None, max_news=5, max_related_stocks=5):
        return {
            "analysis_date": date or "2026-05-27",
            "top_news_json": [{"title": "A", "news_importance_score": 90, "affected_sectors": ["电子"], "affected_themes": ["AI算力"], "impact_direction": "positive", "impact_horizon": "short_term", "reason": "x"}],
            "affected_sectors_json": ["电子"],
            "affected_themes_json": ["AI算力"],
            "related_stocks_json": [{"code": "000001", "name": "N1", "relevance_score": 88, "matched_themes": ["AI算力"], "matched_news_titles": ["A"], "reason": "x"}],
            "market_summary": "ok",
            "risk_notes": ["r"],
        }


def test_daily_market_create_and_latest(monkeypatch):
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(agent_routes, "DailyMarketIntelligenceAgent", DummyDailyAgent)
    client = TestClient(app)
    r = client.post("/agent/daily-market", json={"max_news": 5, "max_related_stocks": 5})
    assert r.status_code == 200
    latest = client.get("/agent/daily-market/latest")
    assert latest.status_code == 200
    data = latest.json()
    assert data["market_summary"] == "ok"
    assert len(data["top_news_json"]) <= 5
    assert len(data["related_stocks_json"]) <= 5
