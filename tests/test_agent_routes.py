import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import agent_routes
from app.database import Base, engine


class DummyAgent:
    def __init__(self, settings):
        pass

    async def analyze_stocks(self, stock_codes):
        return []

    async def market_overview(self):
        return {"market_sentiment": 0, "tech_sector_sentiment": 0}


def test_agent_analyze_fallback_per_code(monkeypatch):
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyAgent)
    client = TestClient(app)
    resp = client.post("/agent/analyze", json={"stock_codes": ["sz002456"], "include_market_overview": True})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["stock_analyses"]) == 1
    row = data["stock_analyses"][0]
    assert row["stock_code"] == "002456"
    assert row["ai_sentiment_score"] == 0

    latest = client.get("/agent/latest")
    assert latest.status_code == 200
    analyses = latest.json().get("analyses", [])
    assert any(x.get("stock_code") == "002456" for x in analyses)
