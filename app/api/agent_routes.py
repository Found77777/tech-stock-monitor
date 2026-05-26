from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.agent.news_agent import NewsAgent
from app.agent.sentiment_scorer import merge_market_overview, score_from_analysis
from app.config import get_settings
from app.database import get_db
from app.models import DailyBar, NewsAnalysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    stock_codes: list[str] | None = None
    include_market_overview: bool = True


@router.post("/analyze")
async def analyze_news(req: AnalyzeRequest, db: Session = Depends(get_db)):
    agent = NewsAgent(get_settings())
    codes = req.stock_codes or [r[0] for r in db.query(DailyBar.code).group_by(DailyBar.code).all()]
    results = {"stock_analyses": [], "market_overview": None}
    if codes:
        analyses = await agent.analyze_stocks(codes)
        for a in analyses:
            scored = score_from_analysis(a)
            rec = {
                "stock_code": a.get("stock_code", ""), "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "raw_analysis": json.dumps(a, ensure_ascii=False), "ai_sentiment_score": scored["ai_sentiment_score"],
                "ai_confidence": scored["ai_confidence"], "ai_policy_boost": scored["ai_policy_boost"],
                "ai_fundamental_boost": scored["ai_fundamental_boost"], "ai_reasons": json.dumps(scored["ai_reasons"], ensure_ascii=False),
            }
            _upsert_news_analysis(db, rec)
            results["stock_analyses"].append(rec)
    if req.include_market_overview:
        overview = await agent.market_overview()
        adj = merge_market_overview(overview)
        results["market_overview"] = {"raw": overview, "adjustments": adj}
        _upsert_market_overview(db, overview, adj)
    db.commit()
    return results


@router.get("/latest")
def get_latest_analysis(db: Session = Depends(get_db)):
    td = db.query(func.max(NewsAnalysis.analysis_date)).scalar()
    if not td:
        return {"analyses": [], "date": None}
    rows = db.query(NewsAnalysis).filter_by(analysis_date=td).order_by(desc(NewsAnalysis.ai_sentiment_score)).all()
    return {"date": td, "analyses": [{"stock_code": r.stock_code, "ai_sentiment_score": r.ai_sentiment_score, "ai_confidence": r.ai_confidence, "ai_policy_boost": r.ai_policy_boost, "ai_fundamental_boost": r.ai_fundamental_boost, "ai_reasons": json.loads(r.ai_reasons) if r.ai_reasons else []} for r in rows]}


def _upsert_news_analysis(db: Session, record: dict):
    existing = db.query(NewsAnalysis).filter_by(stock_code=record["stock_code"], analysis_date=record["analysis_date"]).first()
    if existing:
        for k, v in record.items():
            setattr(existing, k, v)
    else:
        db.add(NewsAnalysis(**record))


def _upsert_market_overview(db: Session, overview: dict, adjustments: dict):
    rec = {
        "stock_code": "MARKET", "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "raw_analysis": json.dumps({"overview": overview, "adjustments": adjustments}, ensure_ascii=False),
        "ai_sentiment_score": adjustments.get("market_sentiment_adj", 0), "ai_confidence": 0,
        "ai_policy_boost": adjustments.get("tech_sector_adj", 0), "ai_fundamental_boost": 0,
        "ai_reasons": json.dumps(adjustments.get("market_reasons", []), ensure_ascii=False),
    }
    _upsert_news_analysis(db, rec)
