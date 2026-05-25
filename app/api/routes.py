"""HTTP API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
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
