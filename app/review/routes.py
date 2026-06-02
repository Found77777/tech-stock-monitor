from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.review.schemas import (
    AIReviewSummaryOut,
    AIReviewSummaryRequest,
    DailyReviewCreate,
    DailyReviewOut,
    PlanDriftOut,
    ReviewStatsOut,
    TradeLogCreate,
    TradeLogOut,
    TradePlanCreate,
    TradePlanOut,
)
from app.review.service import ReviewService
from app.utils.json_utils import sanitize_for_json

router = APIRouter(prefix="/api/review", tags=["review"])
service = ReviewService()


@router.post("/trade-plan", response_model=TradePlanOut)
def upsert_trade_plan(payload: TradePlanCreate, db: Session = Depends(get_db)):
    return sanitize_for_json(service.upsert_trade_plan(db, payload))


@router.get("/trade-plan/{trade_date}")
def get_trade_plan(trade_date: str, db: Session = Depends(get_db)):
    return sanitize_for_json(service.get_trade_plan(db, trade_date) or {})


@router.post("/daily", response_model=DailyReviewOut)
def upsert_daily_review(payload: DailyReviewCreate, db: Session = Depends(get_db)):
    return sanitize_for_json(service.upsert_daily_review(db, payload))


@router.get("/daily/{review_date}")
def get_daily_review(review_date: str, db: Session = Depends(get_db)):
    return sanitize_for_json(service.get_daily_review(db, review_date) or {})


@router.post("/trades", response_model=TradeLogOut)
def create_trade_log(payload: TradeLogCreate, db: Session = Depends(get_db)):
    return sanitize_for_json(service.create_trade_log(db, payload))


@router.get("/trades/{trade_date}")
def list_trade_logs(trade_date: str, db: Session = Depends(get_db)):
    return sanitize_for_json(service.list_trade_logs(db, trade_date))


@router.post("/ai-summary", response_model=AIReviewSummaryOut)
def ai_review_summary(payload: AIReviewSummaryRequest, db: Session = Depends(get_db)):
    return sanitize_for_json(service.ai_summary(db, payload.review_date))


@router.get("/plan-drift", response_model=PlanDriftOut)
def plan_drift(trade_date: str, db: Session = Depends(get_db)):
    return sanitize_for_json(service.plan_drift(db, trade_date))


@router.get("/stats", response_model=ReviewStatsOut)
def review_stats(days: int = 30, db: Session = Depends(get_db)):
    return sanitize_for_json(service.stats(db, days=days))
