from fastapi.testclient import TestClient

from app.api import agent_routes
from app.database import Base, engine, SessionLocal
from app.main import app
from app.models import EnhancedStockScore, StockScore


class DummyAgent:
    def __init__(self, settings):
        pass

    async def analyze_stocks(self, stock_codes):
        out = []
        for c in stock_codes:
            if c == "000001":
                out.append({"stock_code": c, "policy_sentiment": 100, "fundamental_event_score": 100, "industry_momentum": 100, "market_buzz_score": 100, "market_buzz_direction": 100, "macro_impact": 0, "composite_sentiment": 100, "confidence": 10, "key_events": ["x"], "risk_flags": [], "summary": "s"})
            elif c == "000002":
                out.append({"stock_code": c, "policy_sentiment": -100, "fundamental_event_score": -100, "industry_momentum": -100, "market_buzz_score": 100, "market_buzz_direction": -100, "macro_impact": 0, "composite_sentiment": -100, "confidence": 90, "key_events": ["x"], "risk_flags": ["风险1", "风险2"], "summary": "s"})
        return out

    async def market_overview(self):
        return {"market_sentiment": 0, "tech_sector_sentiment": 0}


def _seed_scores(n=12):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(EnhancedStockScore).delete()
    db.query(StockScore).delete()
    for i in range(n):
        code = f"{i+1:06d}"
        db.add(StockScore(code=code, name=f"N{code}", trade_date="2026-05-27", total_score=80-i, trend_score=50, momentum_score=50, relative_strength_score=50, liquidity_score=50, position_score=50, risk_penalty=0, rank=i+1, reasons="[]"))
    db.commit()
    db.close()


def test_analyze_top_only_top10(monkeypatch):
    _seed_scores(30)
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyAgent)
    client = TestClient(app)
    resp = client.post("/agent/analyze-top", json={"top_n": 10, "rerank": True})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 10
    assert all("capital_flow_source" in x for x in items)


def test_analyze_manual_codes_only(monkeypatch):
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyAgent)
    client = TestClient(app)
    resp = client.post("/agent/analyze", json={"stock_codes": ["sz000001"], "include_market_overview": False})
    assert resp.status_code == 200
    rows = resp.json()["stock_analyses"]
    assert len(rows) == 1
    assert rows[0]["stock_code"] == "000001"


def test_ai_adjustment_caps():
    adj_low_conf = agent_routes._calc_ai_adjustment(100, 10, 15, 10, ["ok"])
    assert -3 <= adj_low_conf <= 3
    adj_high_conf = agent_routes._calc_ai_adjustment(100, 90, 15, 10, ["ok"])
    assert -10 <= adj_high_conf <= 10


def test_ai_adjustment_zero_when_no_news():
    adj = agent_routes._calc_ai_adjustment(100, 90, 15, 10, ["未抓取到有效新闻，暂不调整评分"])
    assert adj == 0


def test_analyze_top_rerank_fields(monkeypatch):
    _seed_scores(12)
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyAgent)
    client = TestClient(app)
    resp = client.post("/agent/analyze-top", json={"top_n": 10, "rerank": True})
    assert resp.status_code == 200
    row = resp.json()["items"][0]
    assert "original_rank" in row and "new_rank" in row


def test_capital_flow_proxy_default():
    class S:
        capital_flow_source = "proxy"
    agent_routes._CAPITAL_FLOW_CACHE.clear()
    out = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S())
    assert out["capital_flow_source"] in {"proxy", "proxy_fallback"}


def test_capital_flow_eastmoney_success(monkeypatch):
    import pandas as pd

    class AK:
        @staticmethod
        def stock_individual_fund_flow(stock, market):
            return pd.DataFrame([{"主力净流入-净额": 123456}])

    class S:
        capital_flow_source = "eastmoney"
        capital_flow_sleep_min = 0.0
        capital_flow_sleep_max = 0.0

    agent_routes._CAPITAL_FLOW_CACHE.clear()
    import sys
    sys.modules["akshare"] = AK
    out = agent_routes._fetch_capital_flow_with_cache("600850", "2026-05-27", S())
    assert out["capital_flow_source"] == "real_eastmoney"


def test_capital_flow_eastmoney_fail_to_fallback(monkeypatch):
    class AK:
        @staticmethod
        def stock_individual_fund_flow(stock, market):
            raise RuntimeError("blocked")

    class S:
        capital_flow_source = "eastmoney"
        capital_flow_sleep_min = 0.0
        capital_flow_sleep_max = 0.0

    agent_routes._CAPITAL_FLOW_CACHE.clear()
    import sys
    sys.modules["akshare"] = AK
    out = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S())
    assert out["capital_flow_source"] == "proxy_fallback"


def test_infer_akshare_fund_flow_market():
    assert agent_routes.infer_akshare_fund_flow_market("600850") == "sh"
    assert agent_routes.infer_akshare_fund_flow_market("603236") == "sh"
    assert agent_routes.infer_akshare_fund_flow_market("002465") == "sz"
    assert agent_routes.infer_akshare_fund_flow_market("000001") == "sz"


class DummyAgentNoAlpha:
    def __init__(self, settings):
        pass

    async def fetch_stock_news(self, code):
        items=[{"title":"板块异动消息","source":"新浪财经","publish_time":"2026-05-27","summary":"无公司级事件","url":"u"} for _ in range(7)]
        return items,{"final_return_count":7,"final_news":items,"source_success_counts":{"sina":7},"debug_reason":"ok"}

    async def analyze_stocks(self, stock_codes):
        return []

    async def market_overview(self):
        return {"market_sentiment":0,"tech_sector_sentiment":0}


def test_analyze_top_fetched_news_but_zero_alpha(monkeypatch):
    _seed_scores(12)
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyAgentNoAlpha)
    client = TestClient(app)
    resp = client.post('/agent/analyze-top', json={"top_n":1,"rerank":True})
    assert resp.status_code == 200
    row = resp.json()["items"][0]
    assert row["fetched_news_count"] == 7
    assert "未抓取到有效新闻" not in " ".join(row.get("ai_reasons", []))
    assert row.get("top_news_events")


def test_no_news_fallback_message(monkeypatch):
    class DummyNoNews(DummyAgentNoAlpha):
        async def fetch_stock_news(self, code):
            return [],{"final_return_count":0,"final_news":[],"debug_reason":"all_sources_empty"}
    _seed_scores(12)
    monkeypatch.setattr(agent_routes, "NewsAgent", DummyNoNews)
    client = TestClient(app)
    resp = client.post('/agent/analyze-top', json={"top_n":1,"rerank":True})
    row = resp.json()["items"][0]
    assert row["fetched_news_count"] == 0
    assert any("未抓取到有效新闻" in x for x in row.get("ai_reasons", []))


def test_capital_flow_retry_then_success(monkeypatch):
    calls = {"n": 0}

    class AK:
        @staticmethod
        def stock_individual_fund_flow(stock, market):
            import pandas as pd
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("temp")
            return pd.DataFrame([{"主力净流入-净额": 12}])

    class S:
        capital_flow_source = "eastmoney"
        capital_flow_sleep_min = 0.0
        capital_flow_sleep_max = 0.0
        capital_flow_retry = 3
        capital_flow_cache_enabled = True

    import sys
    sys.modules["akshare"] = AK
    agent_routes._CAPITAL_FLOW_CACHE.clear()
    out = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S())
    assert out["capital_flow_source"] == "real_eastmoney"
    assert out["attempts_used"] == 2
    assert out["success_attempt"] == 2


def test_capital_flow_three_failures():
    class AK:
        @staticmethod
        def stock_individual_fund_flow(stock, market):
            raise RuntimeError("always fail")

    class S:
        capital_flow_source = "eastmoney"
        capital_flow_sleep_min = 0.0
        capital_flow_sleep_max = 0.0
        capital_flow_retry = 3
        capital_flow_cache_enabled = True

    import sys
    sys.modules["akshare"] = AK
    agent_routes._CAPITAL_FLOW_CACHE.clear()
    out = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S())
    assert out["capital_flow_source"] == "proxy_fallback"
    assert out["attempts_used"] == 3


def test_capital_flow_cache_and_force_refresh(monkeypatch):
    calls = {"n": 0}

    class AK:
        @staticmethod
        def stock_individual_fund_flow(stock, market):
            import pandas as pd
            calls["n"] += 1
            return pd.DataFrame([{"主力净流入-净额": 1}])

    class S:
        capital_flow_source = "eastmoney"
        capital_flow_sleep_min = 0.0
        capital_flow_sleep_max = 0.0
        capital_flow_retry = 3
        capital_flow_cache_enabled = True

    import sys
    sys.modules["akshare"] = AK
    agent_routes._CAPITAL_FLOW_CACHE.clear()
    _ = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S(), force_refresh=False)
    _ = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S(), force_refresh=False)
    assert calls["n"] == 1
    _ = agent_routes._fetch_capital_flow_with_cache("000001", "2026-05-27", S(), force_refresh=True)
    assert calls["n"] == 2
