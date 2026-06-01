"""改进的 agent_routes.py - 集成所有优化"""
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
from app.agent.news_alpha_engine import compute_news_alpha
from app.agent.news_alpha_integrator import integrate_news_alpha_to_analysis
from app.agent.news_sources_improved import build_improved_news_sources
from app.agent.sentiment_scorer import merge_market_overview, score_from_analysis
from app.agent.config_validator import validate_agent_config
from app.agent.metrics import agent_metrics
from app.config import get_settings
from app.database import get_db
from app.models import DailyBar, DailyMarketIntelligence, EnhancedStockScore, NewsAlphaSignal, NewsAnalysis, StockScore

router = APIRouter()
logger = logging.getLogger(__name__)
_CAPITAL_FLOW_CACHE: dict[tuple[str, str], dict] = {}


def _norm_code(code: str) -> str:
    c = "".join(ch for ch in str(code or "") if ch.isdigit())
    return c[-6:].zfill(6) if c else ""


def infer_akshare_fund_flow_market(code: str) -> str:
    c = _norm_code(code)
    if c.startswith(("600", "601", "603", "605")):
        return "sh"
    if c.startswith(("000", "001", "002", "003")):
        return "sz"
    if c.startswith(("8", "4")):
        return "bj"
    return "sz"


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


@router.get("/health")
def agent_health(db: Session = Depends(get_db)):
    """✅ 新增：检查 Agent 系统的健康状态"""
    settings = get_settings()
    
    # 验证配置
    config_valid, config_warnings = validate_agent_config(settings)
    
    health_status = {
        "agent_enabled": settings.agent_enabled,
        "agent_debug_mode": settings.agent_debug_mode,
        "news_sources": settings.agent_news_sources.split(","),
        "llm_configured": bool(settings.llm_api_key),
        "tushare_configured": bool(settings.tushare_token),
        "config_valid": config_valid,
        "config_warnings": config_warnings,
        "last_analysis_date": None,
        "metrics": agent_metrics.get_summary(),
    }
    
    # 检查最近的分析
    try:
        last = db.query(NewsAnalysis.analysis_date).order_by(
            NewsAnalysis.analysis_date.desc()
        ).first()
        if last:
            health_status["last_analysis_date"] = last[0]
            logger.info("agent_health last_analysis_date=%s", last[0])
    except Exception as e:
        health_status["last_error"] = str(e)
        logger.exception("agent_health check failed")
    
    logger.info("agent_health status=%s", json.dumps(health_status, default=str, ensure_ascii=False))
    return health_status


@router.post("/analyze")
async def analyze_news(req: AnalyzeRequest, db: Session = Depends(get_db)):
    agent = NewsAgent(get_settings())
    raw_codes = req.stock_codes or [r[0] for r in db.query(DailyBar.code).group_by(DailyBar.code).all()]
    codes = [_norm_code(c) for c in raw_codes if _norm_code(c)]
    logger.info("agent analyze requested stock_codes=%s", codes)
    results = {"stock_analyses": [], "market_overview": None}
    if codes:
        source_debug: dict[str, dict] = {}
        fetched_news_count: dict[str, int] = {}
        if hasattr(agent, "fetch_stock_news"):
            for code in codes:
                items, dbg = await agent.fetch_stock_news(code)
                source_debug[code] = dbg
                fetched_news_count[code] = len(items)
                agent_metrics.record_news_fetch(len(items) > 0)
        else:
            for code in codes:
                fetched_news_count[code] = 0
                source_debug[code] = {"debug_reason": "agent_has_no_fetch_stock_news"}
                agent_metrics.record_news_fetch(False)
        analyses = await agent.analyze_stocks(codes)
        fetched_counts: dict[str, int] = {code: int(fetched_news_count.get(code, 0)) for code in codes}
        by_code = {}
        llm_parse_status = {}
        for a in analyses:
            c = _norm_code(a.get("stock_code", ""))
            if c:
                by_code[c] = a
                fetched_counts[c] = fetched_counts.get(c, 0) + 1
                llm_parse_status[c] = "ok"
                agent_metrics.record_llm_call(True)
        logger.info("agent fetched news count per stock=%s", fetched_counts)
        logger.info("agent fetched/parsed analysis count=%s", len(by_code))

        for code in codes:
            a = by_code.get(code)
            llm_parse_status.setdefault(code, "parse_failed_or_unmentioned")
            is_fallback = False
            if not a:
                is_fallback = True
                agent_metrics.record_llm_call(False)
                # ✅ 改进3：LLM 失败时返回默认中性值，而不是 0
                a = {
                    "stock_code": code,
                    "policy_sentiment": 25,
                    "fundamental_event_score": 30,
                    "industry_momentum": 40,
                    "market_buzz_score": 35,
                    "market_buzz_direction": 0,
                    "macro_impact": 20,
                    "composite_sentiment": 40,
                    "confidence": 0.1,
                    "risk_flags": ["LLM分析失败，使用默认中性值"],
                    "key_events": [],
                    "summary": "LLM分析失败，使用规则引擎",
                }
            if is_fallback:
                scored = {
                    "ai_sentiment_score": 40.0,
                    "ai_confidence": 0.1,
                    "ai_policy_boost": 0.0,
                    "ai_fundamental_boost": 0.0,
                    "ai_risk_flags": ["LLM分析失败"],
                    "ai_reasons": ["LLM分析失败，使用默认中性值"],
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
        results["fetched_news_count"] = fetched_counts
        results["source_debug"] = source_debug
        results["llm_parse_status"] = llm_parse_status
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
    return {"date": td, "analyses": [{"stock_code": r.stock_code, "ai_sentiment_score": r.ai_sentiment_score, "ai_confidence": r.ai_confidence, "ai_policy_boost": r.ai_policy_boost, "ai_fundamental_boost": r.ai_fundamental_boost} for r in rows]}


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


def _fetch_capital_flow_with_cache(code: str, trade_date: str, settings, force_refresh: bool = False) -> dict:
    key = (_norm_code(code), trade_date)
    cache_enabled = bool(getattr(settings, "capital_flow_cache_enabled", True))
    if cache_enabled and not force_refresh and key in _CAPITAL_FLOW_CACHE:
        return _CAPITAL_FLOW_CACHE[key]

    source = str(getattr(settings, "capital_flow_source", "proxy")).lower()
    if source != "eastmoney":
        payload = {
            "capital_flow_source": "proxy",
            "net_inflow_1d": 0.0,
            "net_inflow_5d": 0.0,
            "net_inflow_10d": 0.0,
            "attempts_used": 0,
            "success_attempt": None,
            "capital_flow_error_type": None,
            "capital_flow_error_message": "",
            "capital_flow_source_attempted": source,
        }
        if cache_enabled:
            _CAPITAL_FLOW_CACHE[key] = payload
        return payload

    sleep_min = float(getattr(settings, "capital_flow_sleep_min", 8.0))
    sleep_max = float(getattr(settings, "capital_flow_sleep_max", 18.0))
    retry = max(1, int(getattr(settings, "capital_flow_retry", 3)))
    market = infer_akshare_fund_flow_market(code)
    last_err_type = None
    last_err_msg = ""

    for attempt in range(1, retry + 1):
        try:
            import akshare as ak
            logger.info("capital flow attempt code=%s market=%s attempt=%s status=start", _norm_code(code), market, attempt)
            df = ak.stock_individual_fund_flow(stock=_norm_code(code), market=market)
            if df is None or df.empty:
                raise ValueError("empty fund flow")
            latest = df.iloc[0]
            n1 = _sanitize_num(latest.get("主力净流入-净额", 0), -1e13, 1e13)
            payload = {
                "capital_flow_source": "real_eastmoney",
                "net_inflow_1d": n1,
                "net_inflow_5d": 0.0,
                "net_inflow_10d": 0.0,
                "attempts_used": attempt,
                "success_attempt": attempt,
                "capital_flow_error_type": None,
                "capital_flow_error_message": "",
                "capital_flow_source_attempted": "eastmoney",
            }
            logger.info("capital flow attempt code=%s market=%s attempt=%s status=success", _norm_code(code), market, attempt)
            if cache_enabled:
                _CAPITAL_FLOW_CACHE[key] = payload
            return payload
        except Exception as exc:
            last_err_type = type(exc).__name__
            last_err_msg = str(exc)
            sleep_s = random.uniform(sleep_min, sleep_max) if attempt < retry else 0.0
            logger.warning(
                "capital flow attempt code=%s market=%s attempt=%s status=failure sleep_seconds=%.2f error_type=%s error_message=%s",
                _norm_code(code), market, attempt, sleep_s, last_err_type, last_err_msg,
            )
            if attempt < retry:
                time.sleep(sleep_s)

    payload = {
        "capital_flow_source": "proxy_fallback",
        "net_inflow_1d": 0.0,
        "net_inflow_5d": 0.0,
        "net_inflow_10d": 0.0,
        "attempts_used": retry,
        "success_attempt": None,
        "capital_flow_error_type": last_err_type,
        "capital_flow_error_message": last_err_msg,
        "capital_flow_source_attempted": "eastmoney",
    }
    if cache_enabled:
        _CAPITAL_FLOW_CACHE[key] = payload
    return payload


@router.post("/analyze-top")
async def analyze_top(req: AnalyzeTopRequest, db: Session = Depends(get_db)):
    """✅ 改进1：使用改进的新闻源和集成模块"""
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

    # ✅ 改进1：使用改进的新闻源
    news_sources = build_improved_news_sources(settings)
    out = []
    
    for idx, s in enumerate(base_rows, start=1):
        code = _norm_code(s.code)
        
        try:
            # 使用改进的新闻源获取新闻
            news_items = []
            for source in news_sources:
                try:
                    fetched = await source.fetch([code])
                    news_items.extend(fetched or [])
                    if fetched:
                        agent_metrics.record_news_fetch(True)
                        logger.info("news_fetch source=%s code=%s fetched=%s", source.name, code, len(fetched))
                except Exception as e:
                    agent_metrics.record_news_fetch(False)
                    # ✅ 改进2：记录每个新闻源的错误
                    logger.exception("news_fetch source=%s code=%s failed: %s", source.name, code, e)
            
            stock_meta = {"code": code, "name": s.name or ""}
            
            # ✅ 改进1：使用统一的集成函数
            ai_data = integrate_news_alpha_to_analysis(
                db=db,
                code=code,
                trade_date=trade_date,
                news_items=news_items,
                stock_meta=stock_meta
            )
            
            alpha = ai_data.get("raw_alpha", {})
            alpha_adj = _sanitize_num(alpha.get("news_alpha_adjustment", 0), -10, 10)
            agent_metrics.record_alpha_adjustment(alpha_adj)
            
            fetched_news_count = len(news_items)
            
            base_total = _sanitize_num(float(getattr(s, "base_total_score", 0) or getattr(s, "total_score", 0)), 0, 100)
            capital_adj = _sanitize_num(float(getattr(s, "capital_flow_adjustment", 0)), -8, 8)
            pre_ai_enhanced = _sanitize_num(float(getattr(s, "enhanced_score", 0) or (base_total + capital_adj)), 0, 100)
            ai_score = _sanitize_num(pre_ai_enhanced + alpha_adj, 0, 100)
            flow_data = _fetch_capital_flow_with_cache(s.code, trade_date, settings)
            base_score = base_total

            # persist per-news alpha details
            db.query(NewsAlphaSignal).filter_by(stock_code=code, analysis_date=trade_date).delete()
            for ev in alpha.get("top_news_events", []):
                db.add(NewsAlphaSignal(
                    stock_code=code, analysis_date=trade_date, news_title=str(ev.get("title", "")),
                    news_url="", source="", publish_time="", event_type=str(ev.get("event_type", "unknown")),
                    impact_direction=str(ev.get("impact_direction", "neutral")), impact_horizon=str(ev.get("impact_horizon", "short_term")),
                    relevance_score=_sanitize_num(ev.get("news_relevance_score", 0), 0, 100),
                    importance_score=_sanitize_num(ev.get("news_importance_score", 0), 0, 100),
                    freshness_score=_sanitize_num(ev.get("news_freshness_score", 0), 0, 100),
                    confidence=_sanitize_num(ev.get("confidence", 0), 0, 1),
                    single_news_alpha=_sanitize_num(ev.get("single_news_alpha", 0), -100, 100),
                    alpha_reasons=json.dumps(ev.get("alpha_reasons", []), ensure_ascii=False),
                ))
            if fetched_news_count > 0 and not alpha.get("top_news_events"):
                alpha["top_news_events"] = [
                    {
                        "title": x.get("title", ""),
                        "source": x.get("source", ""),
                        "publish_time": x.get("publish_time", ""),
                        "event_type": "unknown",
                        "impact_direction": "neutral",
                        "relevance_score": 0.0,
                        "importance_score": 0.0,
                        "freshness_score": 50.0,
                        "confidence": 0.0,
                    }
                    for x in news_items[:3]
                ]
            if fetched_news_count > 0 and alpha_adj == 0:
                alpha["news_alpha_summary"] = "已抓取新闻，但未识别出高置信alpha事件（可能为相关性不足/过旧/市场噪音/无公司级事件），暂不调整评分"

            out.append({
                "original_rank": idx,
                "code": _norm_code(s.code),
                "name": s.name,
                "original_score": base_score,
                "ai_adjusted_score": ai_score,
                "ai_sentiment_score": ai_data.get("ai_sentiment_score", 50),
                "ai_confidence": ai_data.get("ai_confidence", 0.0),
                "ai_reasons": ai_data.get("ai_reasons", []),
                "ai_adjustment": alpha_adj,
                "news_alpha_adjustment": alpha_adj,
                "top_news_events": alpha.get("top_news_events", []),
                "news_alpha_summary": alpha.get("news_alpha_summary", ""),
                "risk_flags": alpha.get("risk_flags", []),
                "capital_flow_adjustment": capital_adj,
                "capital_flow_source": flow_data.get("capital_flow_source", "proxy"),
                "fetched_news_count": fetched_news_count,
                "valid_alpha_event_count": len([e for e in alpha.get("top_news_events", []) if abs(float(e.get("single_news_alpha", 0) or 0)) > 0]),
            })
        except Exception as e:
            logger.exception("analyze_top processing failed for code=%s", code)
            # 即使失败也继续处理下一个
            out.append({
                "original_rank": idx,
                "code": code,
                "name": s.name,
                "original_score": 0,
                "ai_adjusted_score": 0,
                "error": str(e),
            })
    
    reranked = sorted(out, key=lambda x: x.get("ai_adjusted_score", 0), reverse=True)
    rank_map = {x["code"]: i + 1 for i, x in enumerate(reranked)}
    for row in out:
        row["new_rank"] = rank_map[row["code"]] if req.rerank else row["original_rank"]
        # persist enhanced score table (non-breaking)
        if "error" not in row:
            es = db.query(EnhancedStockScore).filter_by(code=row["code"], trade_date=trade_date).first()
            payload = {
                "code": row["code"], "name": row["name"], "trade_date": trade_date,
                "base_total_score": row["original_score"], "ai_adjusted_score": row["ai_adjusted_score"],
                "ai_sentiment_score": row["ai_sentiment_score"], "ai_confidence": row["ai_confidence"],
                "ai_reasons": json.dumps(row["ai_reasons"], ensure_ascii=False),
                "original_rank": row["original_rank"], "new_rank": row["new_rank"],
                "ai_adjustment": _sanitize_num(row.get("news_alpha_adjustment", row.get("ai_adjustment", 0)), -10, 10),
                "enhanced_score": row["ai_adjusted_score"],
                "reasons": json.dumps(row.get("risk_flags", []), ensure_ascii=False),
                "enhanced_rank": row["new_rank"],
            }
            if es:
                for k, v in payload.items():
                    setattr(es, k, v)
            else:
                db.add(EnhancedStockScore(**payload))
    logger.info("agent analyze-top rerank result=%s", [(x["code"], x.get("original_rank"), x.get("new_rank")) for x in out if "error" not in x])
    db.commit()
    return {"trade_date": trade_date, "top_n": top_n, "items": sorted(out, key=lambda x: x.get("new_rank", 999))}


@router.get("/news-alpha/latest")
def news_alpha_latest(code: str, db: Session = Depends(get_db)):
    norm = _norm_code(code)
    td = db.query(func.max(NewsAlphaSignal.analysis_date)).filter(NewsAlphaSignal.stock_code == norm).scalar()
    if not td:
        return {"code": norm, "analysis_date": None, "items": []}
    rows = db.query(NewsAlphaSignal).filter_by(stock_code=norm, analysis_date=td).all()
    return {
        "code": norm,
        "analysis_date": td,
        "items": [
            {
                "news_title": r.news_title,
                "event_type": r.event_type,
                "impact_direction": r.impact_direction,
                "impact_horizon": r.impact_horizon,
                "relevance_score": r.relevance_score,
                "importance_score": r.importance_score,
                "freshness_score": r.freshness_score,
                "confidence": r.confidence,
                "single_news_alpha": r.single_news_alpha,
                "alpha_reasons": json.loads(r.alpha_reasons) if r.alpha_reasons else [],
            }
            for r in rows
        ],
    }


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
        return {"analysis_date": None, "top_news_json": [], "affected_sectors_json": [], "affected_themes_json": [], "related_stocks_json": [], "market_summary": "未抓取到有效市场新闻", "risk_notes": []}
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
