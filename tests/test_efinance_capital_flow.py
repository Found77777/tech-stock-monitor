import os
from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

from app.api import agent_routes
from app.api.routes import _capital_flow_adjustment
from app.data_sources.efinance_capital_flow import fetch_efinance_history_bill, normalize_history_bill, without_system_proxies
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import EnhancedStockScore, StockScore


class EFinanceSettings:
    capital_flow_source = "efinance"
    capital_flow_cache_enabled = False
    capital_flow_allow_proxy = False


def _seed_scores(codes):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(EnhancedStockScore).delete()
    db.query(StockScore).delete()
    for i, code in enumerate(codes):
        db.add(StockScore(code=code, name=f"N{code}", trade_date="2026-05-27", total_score=80 - i, trend_score=50, momentum_score=50, relative_strength_score=50, liquidity_score=50, position_score=50, risk_penalty=0, rank=i + 1, reasons="[]"))
    db.commit()
    db.close()


def _history_bill(values):
    return pd.DataFrame({"日期": pd.date_range("2026-05-01", periods=len(values)).strftime("%Y-%m-%d"), "主力净流入": values})


def test_get_history_bill_success_returns_efinance_history_bill(monkeypatch):
    monkeypatch.setattr(agent_routes, "fetch_efinance_history_bill", lambda code: normalize_history_bill(_history_bill([1, 2, -1, 3, 4, 5, 6, 7, 8, 9]), code))
    out = agent_routes._fetch_capital_flow_with_cache("600850", "2026-05-27", EFinanceSettings())
    assert out["capital_flow_source"] == "efinance_history_bill"
    assert 55 <= out["capital_flow_confidence"] <= 95
    assert out["data_confidence"] != out["source_confidence"]
    assert "资金趋势" in out["capital_flow_reason"]
    assert out["capital_flow_is_real"] is True
    assert out["capital_flow_is_estimated"] is False
    assert out["net_inflow_5d"] == 35
    assert out["net_inflow_days_5d"] == 5


def test_proxy_env_is_temporarily_cleared_and_restored(monkeypatch):
    monkeypatch.setenv("http_proxy", "http://proxy.local:7890")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.local:7890")
    monkeypatch.setenv("LLM_HTTP_PROXY", "http://127.0.0.1:7890")
    observed = {}

    class Stock:
        @staticmethod
        def get_history_bill(stock_code):
            observed["http_proxy"] = os.environ.get("http_proxy")
            observed["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY")
            observed["LLM_HTTP_PROXY"] = os.environ.get("LLM_HTTP_PROXY")
            return _history_bill([1, 2, 3, 4, 5])

    import sys
    monkeypatch.setitem(sys.modules, "efinance", SimpleNamespace(stock=Stock()))
    out = fetch_efinance_history_bill("600850")
    assert out["net_inflow_1d"] == 5
    assert observed["http_proxy"] == ""
    assert observed["HTTPS_PROXY"] == ""
    assert observed["LLM_HTTP_PROXY"] == "http://127.0.0.1:7890"
    assert os.environ.get("http_proxy") == "http://proxy.local:7890"
    assert os.environ.get("HTTPS_PROXY") == "http://proxy.local:7890"


def test_missing_main_inflow_column_returns_unavailable(monkeypatch):
    monkeypatch.setattr(agent_routes, "fetch_efinance_history_bill", lambda code: normalize_history_bill(pd.DataFrame({"日期": ["2026-05-01"], "小单净流入": [1]}), code))
    out = agent_routes._fetch_capital_flow_with_cache("600850", "2026-05-27", EFinanceSettings())
    assert out["capital_flow_source"] == "unavailable"
    assert out["capital_flow_confidence"] == 0
    assert out["capital_flow_is_estimated"] is False
    assert out["capital_flow_error_type"] == "KeyError"


def test_single_stock_failure_does_not_break_capital_flow_batch(monkeypatch):
    _seed_scores(["600850", "603236"])

    def fake_fetch(code):
        if code == "600850":
            raise RuntimeError("single stock failed")
        return normalize_history_bill(_history_bill([1, 1, 1, 1, 1, 1]), code)

    class S:
        capital_flow_verify_top_n = 2
        capital_flow_source = "efinance"
        capital_flow_cache_enabled = False
        capital_flow_allow_proxy = False

    monkeypatch.setattr("app.api.routes.get_settings", lambda: S())
    monkeypatch.setattr(agent_routes, "fetch_efinance_history_bill", fake_fetch)
    resp = TestClient(app).post("/verification/capital-flow-top?top_n=2&trade_date=2026-05-27&force_refresh=true")
    assert resp.status_code == 200
    items = resp.json()["results"]
    assert len(items) == 2
    assert {x["capital_flow_source"] for x in items} == {"unavailable", "efinance_history_bill"}


def test_efinance_history_bill_adjustment_is_capped():
    flow = {"capital_flow_source": "efinance_history_bill", "net_inflow_days_5d": 5, "consecutive_net_inflow_days": 5}
    assert _capital_flow_adjustment(flow, 100, 200) == 3.0
    weak_outflow = {"capital_flow_source": "efinance_history_bill", "net_inflow_days_5d": 0, "consecutive_net_inflow_days": 0}
    assert _capital_flow_adjustment(weak_outflow, -100, -200) == -2.0


def test_efinance_failure_never_uses_proxy_when_proxy_not_explicit(monkeypatch):
    class S:
        capital_flow_source = "efinance"
        capital_flow_cache_enabled = False
        capital_flow_allow_proxy = False

    monkeypatch.setattr(agent_routes, "fetch_efinance_history_bill", lambda code: (_ for _ in ()).throw(RuntimeError("blocked")))
    out = agent_routes._fetch_capital_flow_with_cache("600850", "2026-05-27", S())
    assert out["capital_flow_source"] == "unavailable"
    assert out["capital_flow_is_estimated"] is False
    assert out["net_inflow_5d"] == 0.0
