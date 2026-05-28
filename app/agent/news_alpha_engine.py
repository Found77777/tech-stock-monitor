from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


EVENT_TYPES = [
    "policy_catalyst",
    "industry_catalyst",
    "company_order",
    "earnings",
    "product_tech",
    "capacity_expansion",
    "financing",
    "governance",
    "risk_event",
    "market_noise",
    "research_report",
    "unknown",
]


def _txt(news: dict) -> str:
    return f"{news.get('title','')} {news.get('summary','')}".lower()


def classify_news_event(news: dict) -> str:
    t = _txt(news)
    if any(k in t for k in ["处罚", "诉讼", "减持", "爆雷", "违规"]):
        return "risk_event"
    if any(k in t for k in ["订单", "中标", "合同"]):
        return "company_order"
    if any(k in t for k in ["业绩", "预增", "财报", "快报"]):
        return "earnings"
    if any(k in t for k in ["政策", "发改委", "工信部", "国务院"]):
        return "policy_catalyst"
    if any(k in t for k in ["发布", "量产", "突破", "新品", "技术"]):
        return "product_tech"
    if any(k in t for k in ["扩产", "产能"]):
        return "capacity_expansion"
    if any(k in t for k in ["融资", "定增", "股权激励"]):
        return "financing"
    if any(k in t for k in ["高管", "董事", "治理"]):
        return "governance"
    if any(k in t for k in ["研报", "评级", "机构"]):
        return "research_report"
    if any(k in t for k in ["异动", "涨停", "短线", "情绪"]):
        return "market_noise"
    if any(k in t for k in ["产业链", "景气", "供需"]):
        return "industry_catalyst"
    return "unknown"


def score_news_relevance(news: dict, stock_metadata: dict) -> float:
    t = _txt(news)
    code = str(stock_metadata.get("code", ""))
    name = str(stock_metadata.get("name", ""))
    if code and code in t:
        return 95
    if name and name.lower() in t:
        return 92
    rel = 10.0
    for k in ["sector", "theme", "policy_theme", "primary_theme", "secondary_theme"]:
        v = str(stock_metadata.get(k, ""))
        if v and v.lower() in t:
            rel += 18
    return max(0.0, min(100.0, rel))


def score_news_importance(news: dict, event_type: str) -> float:
    m = {
        "company_order": 90,
        "earnings": 88,
        "policy_catalyst": 82,
        "product_tech": 78,
        "capacity_expansion": 72,
        "industry_catalyst": 70,
        "research_report": 55,
        "market_noise": 22,
        "risk_event": 86,
        "financing": 58,
        "governance": 48,
        "unknown": 35,
    }
    return float(m.get(event_type, 35))


def score_news_freshness(news: dict) -> tuple[float, str]:
    p = str(news.get("publish_time", "")).strip()
    if not p:
        return 50.0, "时间缺失，freshness=50"
    try:
        day = datetime.fromisoformat(p[:10]).date()
        d = (datetime.now(timezone.utc).date() - day).days
    except Exception:
        return 50.0, "时间解析失败，freshness=50"
    if d <= 0:
        return 100.0, "当日"
    if d <= 2:
        return 80.0, "1-2天"
    if d <= 5:
        return 60.0, "3-5天"
    if d <= 10:
        return 35.0, "6-10天"
    return 10.0, "10天以上"


def infer_impact_direction(news: dict, event_type: str) -> str:
    t = _txt(news)
    if event_type == "risk_event":
        return "negative"
    if any(k in t for k in ["下修", "亏损", "风险", "下滑", "处罚"]):
        return "negative"
    if any(k in t for k in ["中标", "预增", "突破", "利好", "签约"]):
        return "positive"
    if event_type == "market_noise":
        return "neutral"
    return "neutral"


def _horizon(event_type: str) -> str:
    if event_type in {"market_noise"}:
        return "intraday"
    if event_type in {"policy_catalyst", "industry_catalyst", "company_order", "product_tech", "capacity_expansion"}:
        return "medium_term"
    if event_type == "risk_event":
        return "short_term"
    return "short_term"


def compute_news_alpha(news_items: list[dict], stock_metadata: dict) -> dict[str, Any]:
    if not news_items:
        return {"news_alpha_adjustment": 0.0, "top_news_events": [], "news_alpha_summary": "无有效新闻，AI不调整", "risk_flags": ["无有效新闻"], "confidence": 0.0}
    events = []
    for n in news_items[:5]:
        et = classify_news_event(n)
        rel = score_news_relevance(n, stock_metadata)
        imp = score_news_importance(n, et)
        fresh, fresh_reason = score_news_freshness(n)
        direction = infer_impact_direction(n, et)
        conf = 0.8 if rel >= 70 else 0.5
        sign = -1 if direction == "negative" else (1 if direction == "positive" else 0)
        single = sign * rel * imp * fresh * conf / 10000.0
        events.append(
            {
                "title": n.get("title", ""),
                "event_type": et,
                "impact_direction": direction,
                "impact_horizon": _horizon(et),
                "news_relevance_score": rel,
                "news_importance_score": imp,
                "news_freshness_score": fresh,
                "confidence": conf,
                "single_news_alpha": single,
                "alpha_reasons": [fresh_reason],
            }
        )
    noise = sum(e["single_news_alpha"] for e in events if e["event_type"] == "market_noise")
    core = sum(e["single_news_alpha"] for e in events if e["event_type"] != "market_noise")
    noise = max(-2.0, min(2.0, noise))
    risk_penalty = -8.0 if any(e["event_type"] == "risk_event" and e["impact_direction"] == "negative" for e in events) else 0.0
    adj = core + noise + risk_penalty
    conf = sum(e["confidence"] for e in events) / max(len(events), 1)
    cap = 3.0 if conf < 0.3 else 10.0
    adj = max(-cap, min(cap, adj))
    return {
        "news_alpha_adjustment": float(adj),
        "top_news_events": events,
        "news_alpha_summary": f"事件{len(events)}条，core={core:.2f}, noise={noise:.2f}, risk={risk_penalty:.2f}",
        "risk_flags": ["risk_event"] if risk_penalty < 0 else [],
        "confidence": float(conf),
    }
