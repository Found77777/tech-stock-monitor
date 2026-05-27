"""HTTP API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.agent_routes import _fetch_capital_flow_with_cache, _norm_code, _sanitize_num
from app.config import get_settings
from app.database import get_db
from app.models import EnhancedStockScore, StockScore
from app.schemas import HealthResponse, SystemStatusResponse, UniverseItem
from app.services.analysis_service import AnalysisService
from app.services.history_data_service import HistoryDataService
from app.services.market_data_service import MarketDataService
from app.services.backtest_service import BacktestService
from app.universe.tech_universe import get_mock_tech_universe
from app.utils.json_utils import sanitize_for_json

router = APIRouter()
market_service = MarketDataService()
history_service = HistoryDataService()
analysis_service = AnalysisService()
backtest_service = BacktestService()

@router.get("/", response_model=SystemStatusResponse)
def root() -> SystemStatusResponse:
    from app.config import get_settings
    s = get_settings()
    return SystemStatusResponse(app_name=s.app_name, env=s.app_env, data_source=s.data_source_provider)

@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")

@router.get("/universe", response_model=list[UniverseItem])
def universe() -> list[UniverseItem]:
    return [UniverseItem(**item) for item in get_mock_tech_universe()]

@router.post("/market/refresh")
def market_refresh(db: Session = Depends(get_db)):
    return market_service.refresh_snapshot(db)

@router.get("/market/snapshot")
def market_snapshot(db: Session = Depends(get_db)):
    return market_service.latest_snapshot(db)

@router.get("/market/top-movers")
def market_top_movers(limit: int = 10, db: Session = Depends(get_db)):
    return market_service.top_movers(db, limit=limit)

@router.post('/history/refresh')
def history_refresh(days: int = 120, db: Session = Depends(get_db)):
    return history_service.refresh(db, days=days)

@router.post('/signals/generate')
def signals_generate(db: Session = Depends(get_db)):
    return analysis_service.generate_signals(db)

@router.get('/signals/latest')
def signals_latest(db: Session = Depends(get_db)):
    return sanitize_for_json(analysis_service.latest_signals(db))

@router.post('/scores/generate')
def scores_generate(db: Session = Depends(get_db)):
    return sanitize_for_json(analysis_service.generate_scores(db))

@router.get('/scores/latest')
def scores_latest(db: Session = Depends(get_db)):
    return sanitize_for_json(analysis_service.latest_scores(db))

@router.get('/watchlist/top')
def watchlist_top(limit: int = 20, db: Session = Depends(get_db)):
    return sanitize_for_json(analysis_service.latest_scores(db))[:limit]


@router.post("/verification/capital-flow-top")
def verification_capital_flow_top(top_n: int = 20, trade_date: str | None = None, force_refresh: bool = False, db: Session = Depends(get_db)):
    s = get_settings()
    top_n = min(max(int(top_n or s.capital_flow_verify_top_n), 1), 30)
    td = trade_date or db.query(func.max(StockScore.trade_date)).scalar()
    if not td:
        return {"verified_count": 0, "fallback_count": 0, "failed_count": 0, "results": []}
    base_rows = db.query(StockScore).filter_by(trade_date=td).order_by(desc(StockScore.total_score)).limit(top_n).all()
    results = []
    fallback_count = 0
    failed_count = 0
    for i, row in enumerate(base_rows, start=1):
        flow = _fetch_capital_flow_with_cache(row.code, td, s) if not force_refresh else _fetch_capital_flow_with_cache.__wrapped__(row.code, td, s) if hasattr(_fetch_capital_flow_with_cache, "__wrapped__") else _fetch_capital_flow_with_cache(row.code, td, s)
        n5 = _sanitize_num(flow.get("net_inflow_5d", 0), -1e13, 1e13)
        n10 = _sanitize_num(flow.get("net_inflow_10d", 0), -1e13, 1e13)
        pvr_adj = 0.0
        if n10 > 0 and n5 > 0:
            adj = 6.0
        elif n10 > 0 or n5 > 0:
            adj = 3.0
        else:
            adj = -4.0
        if flow.get("capital_flow_source") == "proxy_fallback":
            adj = max(-2.0, min(2.0, adj))
            fallback_count += 1
        cap_score = _sanitize_num(50 + adj * 6, 0, 100)
        enhanced = _sanitize_num(float(row.total_score) + adj + pvr_adj, 0, 100)
        reason = f"资金流来源={flow.get('capital_flow_source','proxy')} 5日/10日={n5:.0f}/{n10:.0f} 连续净流入={'是' if (n5>0 and n10>0) else '否'} 量价背离={'是' if adj<0 else '否'}"
        es = db.query(EnhancedStockScore).filter_by(code=row.code, trade_date=td).first()
        payload = dict(code=row.code, name=row.name, trade_date=td, base_rank=i, base_total_score=row.total_score, capital_flow_score=cap_score, capital_flow_source=flow.get("capital_flow_source", "proxy"), capital_flow_adjustment=adj, ai_adjustment=0.0, enhanced_score=enhanced, enhanced_rank=i, reasons=reason, ai_adjusted_score=enhanced, ai_sentiment_score=0.0, ai_confidence=0.0, ai_reasons="[]", original_rank=i, new_rank=i)
        if es:
            for k, v in payload.items():
                setattr(es, k, v)
        else:
            db.add(EnhancedStockScore(**payload))
        results.append({"code": _norm_code(row.code), "name": row.name, "base_rank": i, "base_total_score": row.total_score, "capital_flow_source": flow.get("capital_flow_source", "proxy"), "capital_flow_adjustment": adj, "enhanced_score": enhanced, "reasons": reason})
    db.commit()
    return {"verified_count": len(results), "fallback_count": fallback_count, "failed_count": failed_count, "results": results}


@router.get("/watchlist/enhanced-top")
def watchlist_enhanced_top(limit: int = 20, db: Session = Depends(get_db)):
    td = db.query(func.max(EnhancedStockScore.trade_date)).scalar()
    if not td:
        return sanitize_for_json(analysis_service.latest_scores(db))[:limit]
    rows = db.query(EnhancedStockScore).filter_by(trade_date=td).order_by(desc(EnhancedStockScore.enhanced_score)).limit(limit).all()
    out = []
    for r in rows:
        if str(r.name).startswith("N000"):
            continue
        out.append({"enhanced_rank": r.enhanced_rank or r.new_rank, "code": _norm_code(r.code), "name": r.name, "base_rank": r.base_rank or r.original_rank, "base_total_score": r.base_total_score, "capital_flow_score": r.capital_flow_score, "capital_flow_source": r.capital_flow_source, "capital_flow_adjustment": r.capital_flow_adjustment, "ai_adjustment": r.ai_adjustment, "enhanced_score": r.enhanced_score or r.ai_adjusted_score, "reasons": r.reasons or "", "ai_reasons": r.ai_reasons})
    return sanitize_for_json(out)

@router.post("/backtest/factor-ic")
def backtest_factor_ic(db: Session = Depends(get_db)):
    return sanitize_for_json(backtest_service.run_factor_ic_test(db))

@router.post("/backtest/factor-groups")
def backtest_factor_groups(groups: int = 5, db: Session = Depends(get_db)):
    return sanitize_for_json(backtest_service.run_factor_group_test(db, groups=groups))

@router.post("/backtest/signals")
def backtest_signals(db: Session = Depends(get_db)):
    return sanitize_for_json(backtest_service.run_signal_event_study(db))

@router.post("/backtest/top-score")
def backtest_top_score(top_n: int = 20, hold_days: int = 5, transaction_cost_bps: float = 0.0, db: Session = Depends(get_db)):
    return sanitize_for_json(backtest_service.run_top_score_backtest(db, top_n=top_n, hold_days=hold_days, transaction_cost_bps=transaction_cost_bps))

@router.get("/backtest/results/latest")
def backtest_results_latest(db: Session = Depends(get_db)):
    return sanitize_for_json(backtest_service.latest_results(db))
