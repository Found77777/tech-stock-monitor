from __future__ import annotations

import math
from datetime import datetime
from typing import Any

POSITIVE_WORDS = ["中标", "订单", "预增", "突破", "利好", "签约", "政策", "补贴", "增持", "上调", "扩产", "量产", "创新", "获批"]
NEGATIVE_WORDS = ["处罚", "减持", "诉讼", "预亏", "下修", "风险", "亏损", "下滑", "监管", "立案", "终止", "违约"]


def _safe(v, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        x = float(v)
    except Exception:
        return (lo + hi) / 2
    if math.isnan(x) or math.isinf(x):
        return (lo + hi) / 2
    return max(lo, min(hi, x))


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("/", "-")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[: len(fmt)], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _freshness_score(news_items: list[dict]) -> float:
    if not news_items:
        return 0.0
    scores = []
    today = datetime.now().date()
    for item in news_items:
        dt = _parse_dt(item.get("publish_time") or item.get("date"))
        if not dt:
            scores.append(12.0)
            continue
        days = max((today - dt.date()).days, 0)
        if days == 0:
            scores.append(25.0)
        elif days <= 2:
            scores.append(22.0)
        elif days <= 7:
            scores.append(16.0)
        elif days <= 14:
            scores.append(8.0)
        else:
            scores.append(3.0)
    return sum(scores) / len(scores)


def _news_counts(news_items: list[dict]) -> tuple[int, int, int]:
    pos = neg = neutral = 0
    for item in news_items:
        text = f"{item.get('title','')} {item.get('summary','')} {item.get('content','')}"
        p = sum(text.count(w) for w in POSITIVE_WORDS)
        n = sum(text.count(w) for w in NEGATIVE_WORDS)
        if p > n:
            pos += 1
        elif n > p:
            neg += 1
        else:
            neutral += 1
    return pos, neutral, neg


def _source_count(analysis: dict) -> int:
    sources = analysis.get("_source_success_counts") or {}
    if isinstance(sources, dict):
        return len([v for v in sources.values() if int(v or 0) > 0])
    return 0


def _dynamic_confidence(analysis: dict, raw_confidence: float, raw_signal_abs: float) -> float:
    news_items = analysis.get("_news_items") or []
    if not isinstance(news_items, list):
        news_items = []
    news_count = int(analysis.get("_fetched_news_count", len(news_items)) or 0)
    if news_count <= 0:
        return max(10.0, min(20.0, raw_confidence if raw_confidence > 0 else 15.0))
    coverage = min(35.0, news_count * 7.0)
    freshness = _freshness_score(news_items)
    pos, neutral, neg = _news_counts(news_items)
    directional = pos + neg
    consistency = 8.0 if directional == 0 else 20.0 * abs(pos - neg) / max(directional, 1)
    source_score = min(10.0, _source_count(analysis) * 3.5)
    llm_quality = 0.0
    if analysis.get("llm_fallback"):
        llm_quality = 8.0
    else:
        field_count = sum(1 for k in ["policy_sentiment", "fundamental_event_score", "industry_momentum", "market_buzz_direction", "composite_sentiment", "summary"] if analysis.get(k) not in (None, ""))
        llm_quality = min(20.0, field_count * 3.5)
    llm_quality = max(llm_quality, min(20.0, raw_confidence * 0.2))
    signal_bonus = min(10.0, raw_signal_abs / 10.0)
    return round(_safe(coverage + freshness + consistency + source_score + llm_quality + signal_bonus, 10, 95), 2)


def _reason_summary(analysis: dict, ai_sentiment: float, confidence: float) -> str:
    news_items = analysis.get("_news_items") or []
    news_count = int(analysis.get("_fetched_news_count", len(news_items) if isinstance(news_items, list) else 0) or 0)
    if news_count <= 0:
        return "未抓取到有效新闻，AI维持低置信中性判断，暂不调整评分"
    pos, neutral, neg = _news_counts(news_items if isinstance(news_items, list) else [])
    recent = 0
    today = datetime.now().date()
    for item in news_items if isinstance(news_items, list) else []:
        dt = _parse_dt(item.get("publish_time") or item.get("date"))
        if dt and max((today - dt.date()).days, 0) <= 7:
            recent += 1
    direction = "偏正面" if ai_sentiment >= 60 else ("偏负面" if ai_sentiment <= 40 else "中性")
    return f"近7天发现{recent}条相关新闻；共抓取{news_count}条；其中{pos}条利好、{neutral}条中性、{neg}条利空；DeepSeek/规则综合判断情绪{direction}，置信度{confidence:.0f}%"


def score_from_analysis(analysis: dict) -> dict:
    policy = _safe(analysis.get("policy_sentiment", 0), -100, 100)
    fundamental = _safe(analysis.get("fundamental_event_score", 0), -100, 100)
    industry = _safe(analysis.get("industry_momentum", 0), -100, 100)
    buzz_score = _safe(analysis.get("market_buzz_score", 0), 0, 100)
    buzz_dir = _safe(analysis.get("market_buzz_direction", 0), -100, 100)
    macro = _safe(analysis.get("macro_impact", 0), -100, 100)
    composite = _safe(analysis.get("composite_sentiment", 0), -100, 100)
    raw_confidence = _safe(analysis.get("confidence", 0), 0, 100)
    raw = 0.25 * policy + 0.2 * fundamental + 0.2 * industry + 0.1 * (buzz_dir * buzz_score / 100) + 0.1 * macro + 0.15 * composite
    raw_abs = abs(raw)
    confidence = _dynamic_confidence(analysis, raw_confidence, raw_abs)
    news_count = int(analysis.get("_fetched_news_count", len(analysis.get("_news_items") or [])) or 0)
    if news_count <= 0 and raw_abs < 1:
        ai_sentiment = 50.0
    else:
        # Let the signal move the score directly; confidence affects boosts, not whether visible sentiment collapses to 50.
        ai_sentiment = _safe(50 + raw * 0.55, 0, 100)
        if raw_abs < 5 and news_count > 0:
            pos, _, neg = _news_counts(analysis.get("_news_items") or [])
            ai_sentiment = _safe(50 + (pos - neg) * 6, 0, 100)
    cf = confidence / 100
    summary = _reason_summary(analysis, ai_sentiment, confidence)
    return {
        "ai_sentiment_score": round(ai_sentiment, 2),
        "ai_confidence": round(confidence, 2),
        "ai_policy_boost": round(_safe(policy * 0.15 * cf, -15, 15), 2),
        "ai_fundamental_boost": round(_safe(fundamental * 0.10 * cf, -10, 10), 2),
        "ai_risk_flags": analysis.get("risk_flags", []) if isinstance(analysis.get("risk_flags", []), list) else [],
        "ai_reason_summary": summary,
        "ai_reasons": [summary, f"AI情绪评分：{ai_sentiment:.0f}/100（动态置信度{confidence:.0f}%）"],
    }


def merge_market_overview(overview: dict) -> dict:
    mkt = _safe(overview.get("market_sentiment", 0), -100, 100)
    tech = _safe(overview.get("tech_sector_sentiment", 0), -100, 100)
    return {"market_sentiment_adj": round(_safe(mkt * 0.10, -10, 10), 2), "tech_sector_adj": round(_safe(tech * 0.10, -10, 10), 2), "market_reasons": [f"市场整体情绪：{mkt:.0f}，科技板块：{tech:.0f}"]}
