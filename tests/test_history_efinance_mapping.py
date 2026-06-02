import pandas as pd

from app.data_sources.efinance_source import EFinanceDataSource
from app.factors.liquidity import add_liquidity_factors
from app.scoring.score_engine import compute_score
from app.services.history_data_service import _estimate_amount_if_missing, _history_fallback_chain


def test_efinance_get_quote_history_maps_amount_and_turnover():
    raw = pd.DataFrame([
        {"日期": "2026-05-20", "开盘": "10", "收盘": "10.5", "最高": "11", "最低": "9.8", "成交量": "12300", "成交额": "45678901", "换手率": "8.50", "涨跌幅": "2.3"}
    ])
    df = EFinanceDataSource().normalize_history_df(raw, "sh600850")
    row = df.iloc[0]
    assert row["code"] == "600850"
    assert row["trade_date"] == "2026-05-20"
    assert row["amount"] == 45678901
    assert row["turnover_rate"] == 8.50
    assert row["pct_change"] == 2.3


def test_history_fallback_prefers_efinance_then_sina(monkeypatch):
    monkeypatch.setenv("USE_MOCK_DATA", "false")
    monkeypatch.setenv("HISTORY_DATA_SOURCE", "efinance")
    from app.config import get_settings
    get_settings.cache_clear()
    try:
        assert _history_fallback_chain("efinance")[:2] == ["efinance", "sina"]
    finally:
        get_settings.cache_clear()


def test_sina_fallback_amount_can_be_estimated_from_close_volume():
    row = {"code": "600850", "trade_date": "2026-05-20", "close": 10.5, "volume": 1000, "amount": None, "turnover_rate": None}
    out = _estimate_amount_if_missing(row, "sina")
    assert out["amount"] == 10.5 * 1000 * 100
    assert out["_amount_estimated"] is True


def test_turnover_missing_but_amount_present_liquidity_score_positive():
    df = pd.DataFrame([
        {"trade_date": f"2026-05-{i:02d}", "amount": 60_000_000, "volume": 1000, "turnover_rate": None}
        for i in range(1, 22)
    ])
    out = add_liquidity_factors(df, min_avg_amount=50_000_000)
    assert out.iloc[-1]["avg_amount_20d"] >= 50_000_000
    assert out.iloc[-1]["liquidity_score"] > 0


def test_score_reasons_show_liquidity_amount_turnover_and_estimation_note():
    row = {
        "code": "600850",
        "close": 10,
        "volume": 1000,
        "amount": 100_000_000,
        "amount_estimated": True,
        "avg_amount_20d": 100_000_000,
        "avg_turnover_20d": None,
        "liquidity_score": 70,
        "net_inflow_1d": 0,
        "net_inflow_5d": 0,
        "net_inflow_10d": 0,
        "amount_ratio_5d": 1.2,
        "volume_ratio_5d": 1.2,
        "price_volume_resonance": 0,
        "distance_to_ma20": 0,
        "distance_to_ma60": 0,
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.3,
        "percentile_250d": 40,
        "consolidation_days": 10,
        "ma_structure_score": 50,
        "stock_return_5d": 0,
        "stock_return_10d": 0,
        "stock_return_20d": 0,
        "relative_return_vs_sector": 0,
        "ma20_slope": 0,
        "ma60_slope": 0,
        "ma120_slope": 0,
        "fundamental_quality": "medium",
        "policy_theme": "信创",
        "theme": "信创",
    }
    result = compute_score(row)
    text = "\n".join(result["reasons"])
    assert "avg_amount_20d=100000000" in text
    assert "avg_turnover_20d=N/A" in text
    assert "成交额由 close*volume*100 估算" in text


def test_history_refresh_falls_back_to_sina_and_estimates_amount(monkeypatch):
    from app.database import Base, SessionLocal, engine
    from app.models import DailyBar, StockSnapshot
    from app.services.history_data_service import HistoryDataService

    Base.metadata.create_all(bind=engine)

    class FakeEFinance:
        def fetch_daily_bars(self, code: str, start_date: str, end_date: str):
            return pd.DataFrame([{"code": code, "name": None, "trade_date": "2026-05-20", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000, "amount": None, "pct_change": 1.0, "turnover_rate": None}])

    class FakeSina:
        def fetch_daily_bars(self, code: str, start_date: str, end_date: str):
            return pd.DataFrame([{"code": code, "name": None, "trade_date": "2026-05-20", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000, "amount": None, "pct_change": 1.0, "turnover_rate": None}])

    db = SessionLocal()
    try:
        db.query(DailyBar).delete(synchronize_session=False)
        db.query(StockSnapshot).delete(synchronize_session=False)
        db.add(StockSnapshot(code="600850", name="电科数字", price=10, pct_change=0, change=0, volume=0, amount=90_000_000, turnover_rate=0, pe=0, pb=0, total_market_cap=0, float_market_cap=0, timestamp="2026-05-20 10:00:00"))
        db.commit()
        svc = HistoryDataService()
        monkeypatch.setattr(svc, "_resolve_source", lambda: (FakeEFinance(), "efinance"))
        monkeypatch.setattr(svc, "_history_sources", lambda: [(FakeEFinance(), "efinance"), (FakeSina(), "sina")])
        result = svc.refresh(db, days=5)
        assert result["inserted"] == 1
        row = db.query(DailyBar).filter_by(code="600850", trade_date="2026-05-20").first()
        assert row is not None
        assert row.amount == 10.5 * 1000 * 100
        assert row.turnover_rate is None
    finally:
        db.close()
