from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import DailyReview, TradeLog, TradePlan
from app.review.service import ReviewService


def _reset_review_tables():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(TradeLog).delete()
    db.query(DailyReview).delete()
    db.query(TradePlan).delete()
    db.commit()
    db.close()


def test_trade_plan_log_drift_ai_summary_and_stats_api():
    _reset_review_tables()
    client = TestClient(app)
    day = "2026-06-02"
    plan = {
        "trade_date": day,
        "watch_symbols": ["002465"],
        "focus_sectors": ["通信"],
        "market_view": "震荡偏强",
        "bull_case": "资金回流科技",
        "bear_case": "缩量回落",
        "max_position": 10000,
        "planned_trades": [{"symbol": "002465", "action": "buy"}],
        "risk_notes": ["不追高"],
    }
    r = client.post("/api/review/trade-plan", json=plan)
    assert r.status_code == 200
    assert r.json()["watch_symbols"] == ["002465"]

    review = {
        "review_date": day,
        "status": "completed",
        "market_score": 70,
        "market_environment": "科技轮动",
        "emotion_score": 80,
        "execution_score": 60,
        "discipline_score": 75,
        "daily_pnl": -120,
        "max_drawdown": -3.5,
        "largest_winner": "",
        "largest_loser": "002465",
        "mistakes": ["追高"],
        "good_decisions": ["控制仓位"],
        "lessons_learned": ["等待确认"],
        "tomorrow_plan": "降低频率",
    }
    assert client.post("/api/review/daily", json=review).status_code == 200

    log = {
        "trade_date": day,
        "symbol": "600850",
        "action": "buy",
        "quantity": 1000,
        "entry_price": 12,
        "exit_price": 11.8,
        "pnl": -200,
        "planned_trade": False,
        "actual_reason": "情绪追高",
        "result_score": 40,
        "notes": "计划外",
    }
    assert client.post("/api/review/trades", json=log).status_code == 200

    drift = client.get(f"/api/review/plan-drift?trade_date={day}")
    assert drift.status_code == 200
    body = drift.json()
    assert body["discipline_score"] < 100
    assert {x["type"] for x in body["violations"]} >= {"unplanned_trade", "emotional_trade"}

    summary = client.post("/api/review/ai-summary", json={"review_date": day})
    assert summary.status_code == 200
    assert "suggestions" in summary.json()

    stats = client.get("/api/review/stats?days=30")
    assert stats.status_code == 200
    assert stats.json()["days"] >= 1


def test_daily_review_draft_is_idempotent():
    _reset_review_tables()
    db = SessionLocal()
    service = ReviewService()
    first = service.create_review_draft(db, "2026-06-02")
    second = service.create_review_draft(db, "2026-06-02")
    db.close()
    assert first["id"] == second["id"]
    assert first["status"] == "pending"
