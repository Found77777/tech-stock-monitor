from __future__ import annotations

import math


def _safe(v, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        x = float(v)
    except Exception:
        return (lo + hi) / 2
    if math.isnan(x) or math.isinf(x):
        return (lo + hi) / 2
    return max(lo, min(hi, x))


def score_from_analysis(analysis: dict) -> dict:
    policy = _safe(analysis.get("policy_sentiment", 0), -100, 100)
    fundamental = _safe(analysis.get("fundamental_event_score", 0), -100, 100)
    industry = _safe(analysis.get("industry_momentum", 0), -100, 100)
    buzz_score = _safe(analysis.get("market_buzz_score", 0), 0, 100)
    buzz_dir = _safe(analysis.get("market_buzz_direction", 0), -100, 100)
    macro = _safe(analysis.get("macro_impact", 0), -100, 100)
    composite = _safe(analysis.get("composite_sentiment", 0), -100, 100)
    confidence = _safe(analysis.get("confidence", 30), 0, 100)
    raw = 0.25 * policy + 0.2 * fundamental + 0.2 * industry + 0.1 * (buzz_dir * buzz_score / 100) + 0.1 * macro + 0.15 * composite
    ai_sentiment = _safe(50 + raw / 2, 0, 100)
    cf = confidence / 100
    ai_sentiment = 50 + (ai_sentiment - 50) * cf
    return {
        "ai_sentiment_score": round(ai_sentiment, 2),
        "ai_confidence": round(confidence, 2),
        "ai_policy_boost": round(_safe(policy * 0.15 * cf, -15, 15), 2),
        "ai_fundamental_boost": round(_safe(fundamental * 0.10 * cf, -10, 10), 2),
        "ai_risk_flags": analysis.get("risk_flags", []) if isinstance(analysis.get("risk_flags", []), list) else [],
        "ai_reasons": [f"AI情绪评分：{ai_sentiment:.0f}/100（置信度{confidence:.0f}%）"],
    }


def merge_market_overview(overview: dict) -> dict:
    mkt = _safe(overview.get("market_sentiment", 0), -100, 100)
    tech = _safe(overview.get("tech_sector_sentiment", 0), -100, 100)
    return {"market_sentiment_adj": round(_safe(mkt * 0.10, -10, 10), 2), "tech_sector_adj": round(_safe(tech * 0.10, -10, 10), 2), "market_reasons": [f"市场整体情绪：{mkt:.0f}，科技板块：{tech:.0f}"]}
