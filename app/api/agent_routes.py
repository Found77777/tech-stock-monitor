from __future__ import annotations

import json
import logging
import random
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.agent.daily_market_agent import DailyMarketIntelligenceAgent
from app.agent.news_agent import NewsAgent
from app.agent.sentiment_scorer import merge_market_overview, score_from_analysis
from app.config import get_settings
from app.database import get_db
from app.models import DailyBar, DailyMarketIntelligence, EnhancedStockScore, NewsAnalysis, StockScore

router = APIRouter()
logger = logging.getLogger(__name__)
_CAPITAL_FLOW_CACHE: dict[tuple[str, str], dict] = {}


def _norm_code(code: str) -> str:
    c = "".join(ch for ch in str(code or "") if ch.isdigit())
    return c[-6:].zfill(6) if c else ""


class AnalyzeRequest(BaseModel):
    stock_codes: list[str] | None = None
    include_market_overview: bool = True


class AnalyzeTopRequest(BaseModel):
    top_n: int = 10
    date: str | None = None
    rerank: bool = True


class DailyMarketRequest(BaseModel):
    date: str | None = None
    max_news: int = 5
    max_related_stocks: int = 5


@router.post("/analyze")
async def analyze_news(req: AnalyzeRequest, db: Session = Depends(get_db)):
    agent = NewsAgent(get_settings())
    raw_codes = req.stock_codes or [r[0] for r in db.query(DailyBar.code).group_by(DailyBar.code).all()]
    codes = [_norm_code(c) for c in raw_codes if _norm_code(c)]
    logger.info("agent analyze requested stock_codes=%s", codes)
    results = {"stock_analyses": [], "market_overview": None}
    if codes:
        analyses = await agent.analyze_stocks(codes)
        fetched_counts: dict[str, int] = {code: 0 for code in codes}
        by_code = {}
        for a in analyses:
            c = _norm_code(a.get("stock_code", ""))
            if c:
                by_code[c] = a
                fetched_counts[c] = fetched_counts.get(c, 0) + 1
        logger.info("agent fetched news count per stock=%s", fetched_counts)
        logger.info("agent fetched/parsed analysis count=%s", len(by_code))

        for code in codes:
            a = by_code.get(code)
            is_fallback = False
            if not a:
                is_fallback = True
                a = {
                    "stock_code": code,
                    "policy_sentiment": 0,
                    "fundamental_event_score": 0,
                    "industry_momentum": 0,
                    "market_buzz_score": 0,
                    "market_buzz_direction": 0,
                    "macro_impact": 0,
                    "composite_sentiment": 0,
                    "confidence": 0,
                    "risk_flags": ["未抓取到有效新闻，暂不调整评分"],
                    "key_events": [],
                    "summary": "未抓取到有效新闻，暂不调整评分",
                }
            if is_fallback:
                scored = {
                    "ai_sentiment_score": 0.0,
                    "ai_confidence": 0.0,
                    "ai_policy_boost": 0.0,
                    "ai_fundamental_boost": 0.0,
                    "ai_risk_flags": ["未抓取到有效新闻，暂不调整评分"],
                    "ai_reasons": ["未抓取到有效新闻，暂不调整评分"],
                }
            else:
                scored = score_from_analysis(a)
            rec = {
                "stock_code": code, "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "raw_analysis": json.dumps(a, ensure_ascii=False), "ai_sentiment_score": scored["ai_sentiment_score"],
                "ai_confidence": scored["ai_confidence"], "ai_policy_boost": scored["ai_policy_boost"],
                "ai_fundamental_boost": scored["ai_fundamental_boost"], "ai_reasons": json.dumps(scored["ai_reasons"], ensure_ascii=False),
            }
            _upsert_news_analysis(db, rec)
            results["stock_analyses"].append(rec)
        logger.info("agent generated stock analysis count=%s", len(results["stock_analyses"]))
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


def _sanitize_num(v: float, lo: float = -1000, hi: float = 1000) -> float:
    import math
    try:
        x = float(v)
    except Exception:
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return max(lo, min(hi, x))


def _calc_ai_adjustment(ai_sentiment: float, ai_conf: float, ai_policy: float, ai_fund: float, ai_reasons: list[str]) -> float:
    # fallback no-news => no adjustment
    if ai_reasons and "未抓取到有效新闻" in " ".join(ai_reasons):
        return 0.0
    sentiment_adj = (_sanitize_num(ai_sentiment, 0, 100) - 50.0) * 0.08
    raw = sentiment_adj + _sanitize_num(ai_policy, -15, 15) + _sanitize_num(ai_fund, -10, 10)
    risk_penalty = 0.0
    if isinstance(ai_reasons, list):
        risk_penalty = min(6.0, sum(1 for r in ai_reasons if "风险" in str(r)) * 2.0)
    adj = raw - risk_penalty
    cap = 3.0 if _sanitize_num(ai_conf, 0, 100) < 30 else 10.0
    return _sanitize_num(adj, -cap, cap)


def _fetch_capital_flow_with_cache(code: str, trade_date: str, settings) -> dict:
    key = (_norm_code(code), trade_date)
    if key in _CAPITAL_FLOW_CACHE:
        return _CAPITAL_FLOW_CACHE[key]

    source = str(getattr(settings, "capital_flow_source", "proxy")).lower()
    if source != "eastmoney":
        payload = {"capital_flow_source": "proxy", "net_inflow_1d": 0.0, "net_inflow_5d": 0.0, "net_inflow_10d": 0.0}
        _CAPITAL_FLOW_CACHE[key] = payload
        return payload

    sleep_min = float(getattr(settings, "capital_flow_sleep_min", 1.5))
    sleep_max = float(getattr(settings, "capital_flow_sleep_max", 3.0))
    for attempt in range(3):  # 1 + 2 retries
        try:
            import akshare as ak
            df = ak.stock_individual_fund_flow(stock=_norm_code(code), market="沪深京A股")
            if df is None or df.empty:
                raise ValueError("empty fund flow")
            latest = df.iloc[0]
            n1 = _sanitize_num(latest.get("主力净流入-净额", 0), -1e13, 1e13)
            payload = {"capital_flow_source": "real_eastmoney", "net_inflow_1d": n1, "net_inflow_5d": 0.0, "net_inflow_10d": 0.0}
            _CAPITAL_FLOW_CACHE[key] = payload
            return payload
        except Exception as exc:
            logger.warning("capital flow fetch failed code=%s attempt=%s err=%s", code, attempt + 1, exc)
            if attempt < 2:
                time.sleep(random.uniform(sleep_min, sleep_max))
    payload = {"capital_flow_source": "proxy_fallback", "net_inflow_1d": 0.0, "net_inflow_5d": 0.0, "net_inflow_10d": 0.0}
    _CAPITAL_FLOW_CACHE[key] = payload
    return payload


@router.post("/analyze-top")
async def analyze_top(req: AnalyzeTopRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    top_n_default = int(getattr(settings, "capital_flow_top_n", 10))
    top_n = int(req.top_n or top_n_default)
    if top_n <= 0:
        raise HTTPException(status_code=400, detail="top_n must be > 0")
    if top_n > 20:
        raise HTTPException(status_code=400, detail="top_n too large; max is 20")

    trade_date = req.date or db.query(func.max(EnhancedStockScore.trade_date)).scalar() or db.query(func.max(StockScore.trade_date)).scalar()
    if not trade_date:
        return {"items": [], "message": "no score data"}
    base_rows = db.query(EnhancedStockScore).filter_by(trade_date=trade_date).order_by(desc(EnhancedStockScore.enhanced_score)).limit(top_n).all()
    if not base_rows:
        base_rows = db.query(StockScore).filter_by(trade_date=trade_date).order_by(desc(StockScore.total_score)).limit(top_n).all()
    if not base_rows:
        return {"items": [], "message": "no score rows in date"}
    codes = [_norm_code(x.code) for x in base_rows]
    logger.info("agent analyze-top initial top_n codes=%s", codes)
    logger.info("agent analyze-top llm_call_count=%s", 1 if codes else 0)

    # reuse analyze flow logic for specified codes only
    analyze_req = AnalyzeRequest(stock_codes=codes, include_market_overview=True)
    await analyze_news(analyze_req, db)

    news_rows = db.query(NewsAnalysis).filter_by(analysis_date=datetime.now().strftime("%Y-%m-%d")).all()
    news_map = { _norm_code(n.stock_code): n for n in news_rows if n.stock_code != "MARKET" }
    out = []
    for idx, s in enumerate(base_rows, start=1):
        n = news_map.get(_norm_code(s.code))
        ai_sent = _sanitize_num(getattr(n, "ai_sentiment_score", 0), 0, 100) if n else 0.0
        ai_conf = _sanitize_num(getattr(n, "ai_confidence", 0), 0, 100) if n else 0.0
        ai_pol = _sanitize_num(getattr(n, "ai_policy_boost", 0), -15, 15) if n else 0.0
        ai_fun = _sanitize_num(getattr(n, "ai_fundamental_boost", 0), -10, 10) if n else 0.0
        ai_reasons = json.loads(n.ai_reasons) if (n and n.ai_reasons) else ["未抓取到有效新闻，暂不调整评分"]
        adj = _calc_ai_adjustment(ai_sent, ai_conf, ai_pol, ai_fun, ai_reasons)
        ai_score = _sanitize_num(float(getattr(s, "enhanced_score", 0) or getattr(s, "base_total_score", 0) or getattr(s, "total_score", 0)) + adj, 0, 100)
        flow_data = _fetch_capital_flow_with_cache(s.code, trade_date, settings)
        base_score = _sanitize_num(float(getattr(s, "base_total_score", 0) or getattr(s, "total_score", 0)), 0, 100)
        out.append({
            "original_rank": idx,
            "code": _norm_code(s.code),
            "name": s.name,
            "original_score": base_score,
            "ai_adjusted_score": ai_score,
            "ai_sentiment_score": ai_sent,
            "ai_confidence": ai_conf / 100.0,
            "ai_reasons": ai_reasons,
              "capital_flow_source": flow_data.get("capital_flow_source", "proxy"),
        })
    reranked = sorted(out, key=lambda x: x["ai_adjusted_score"], reverse=True)
    rank_map = {x["code"]: i + 1 for i, x in enumerate(reranked)}
    for row in out:
        row["new_rank"] = rank_map[row["code"]] if req.rerank else row["original_rank"]
        # persist enhanced score table (non-breaking)
        es = db.query(EnhancedStockScore).filter_by(code=row["code"], trade_date=trade_date).first()
        payload = {
            "code": row["code"], "name": row["name"], "trade_date": trade_date,
            "base_total_score": row["original_score"], "ai_adjusted_score": row["ai_adjusted_score"],
            "ai_sentiment_score": row["ai_sentiment_score"], "ai_confidence": row["ai_confidence"],
            "ai_reasons": json.dumps(row["ai_reasons"], ensure_ascii=False),
            "original_rank": row["original_rank"], "new_rank": row["new_rank"],
            "ai_adjustment": _sanitize_num(row["ai_adjusted_score"] - row["original_score"], -10, 10),
            "enhanced_score": row["ai_adjusted_score"],
            "enhanced_rank": row["new_rank"],
        }
        if es:
            for k, v in payload.items():
                setattr(es, k, v)
        else:
            db.add(EnhancedStockScore(**payload))
    logger.info("agent analyze-top rerank result=%s", [(x["code"], x["original_rank"], x["new_rank"]) for x in out])
    db.commit()
    return {"trade_date": trade_date, "top_n": top_n, "items": sorted(out, key=lambda x: x["new_rank"])}


@router.post("/daily-market")
async def daily_market(req: DailyMarketRequest, db: Session = Depends(get_db)):
    max_news = max(1, min(int(req.max_news or 5), 5))
    max_related_stocks = max(1, min(int(req.max_related_stocks or 5), 5))
    agent = DailyMarketIntelligenceAgent(get_settings())
    data = await agent.run(date=req.date, max_news=max_news, max_related_stocks=max_related_stocks)
    analysis_date = data["analysis_date"]
    row = db.query(DailyMarketIntelligence).filter_by(analysis_date=analysis_date).first()
    payload = {
        "analysis_date": analysis_date,
        "top_news_json": json.dumps(data.get("top_news_json", []), ensure_ascii=False),
        "affected_sectors_json": json.dumps(data.get("affected_sectors_json", []), ensure_ascii=False),
        "affected_themes_json": json.dumps(data.get("affected_themes_json", []), ensure_ascii=False),
        "related_stocks_json": json.dumps(data.get("related_stocks_json", []), ensure_ascii=False),
        "market_summary": str(data.get("market_summary", "")),
        "risk_notes": json.dumps(data.get("risk_notes", []), ensure_ascii=False),
    }
    if row:
        for k, v in payload.items():
            setattr(row, k, v)
    else:
        db.add(DailyMarketIntelligence(**payload))
    db.commit()
    return data


@router.get("/daily-market/latest")
def daily_market_latest(db: Session = Depends(get_db)):
    td = db.query(func.max(DailyMarketIntelligence.analysis_date)).scalar()
    if not td:
        return {"analysis_date": None, "top_news_json": [], "affected_sectors_json": [], "affected_themes_json": [], "related_stocks_json": [], "market_summary": "未抓取到有效市场新闻", "risk_notes": ["新闻源为空，未进行主题映射"]}
    row = db.query(DailyMarketIntelligence).filter_by(analysis_date=td).first()
    return {
        "analysis_date": row.analysis_date,
        "top_news_json": json.loads(row.top_news_json) if row.top_news_json else [],
        "affected_sectors_json": json.loads(row.affected_sectors_json) if row.affected_sectors_json else [],
        "affected_themes_json": json.loads(row.affected_themes_json) if row.affected_themes_json else [],
        "related_stocks_json": json.loads(row.related_stocks_json) if row.related_stocks_json else [],
        "market_summary": row.market_summary or "",
        "risk_notes": json.loads(row.risk_notes) if row.risk_notes else [],
    }
