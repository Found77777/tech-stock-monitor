from __future__ import annotations

from .event_classifier import classify_event
from .freshness_model import freshness_score
from .importance_model import importance_score
from .news_deduper import dedupe_news
from .relevance_model import relevance_score


def _direction(text: str, event_type: str) -> str:
    t = (text or "").lower()
    if event_type in {"risk_event", "litigation", "export_control"}:
        return "negative"
    if any(k in t for k in ["中标", "预增", "突破", "利好"]):
        return "positive"
    if any(k in t for k in ["预亏", "处罚", "减持", "下修"]):
        return "negative"
    return "neutral"


def aggregate_news_alpha(news_items: list[dict], stock_meta: dict) -> dict:
    items = dedupe_news(news_items)[:5]
    if not items:
        return {"news_alpha_adjustment": 0.0, "top_news_events": [], "news_alpha_summary": "无有效新闻，AI不调整", "confidence": 0.0, "risk_flags": ["no_news"]}
    events = []
    for n in items:
        text = f"{n.get('title','')} {n.get('summary','')}"
        event = classify_event(text)
        rel = relevance_score(text, stock_meta)
        imp = importance_score(event)
        fresh = freshness_score(n.get("publish_time"))
        conf = 0.9 if rel >= 90 else (0.7 if rel >= 70 else 0.4)
        direction = _direction(text, event)
        sign = 1 if direction == "positive" else (-1 if direction == "negative" else 0)
        single = sign * rel * imp * fresh * conf / 10000.0
        events.append({"title": n.get("title", ""), "event_type": event, "impact_direction": direction, "relevance": rel, "importance": imp, "freshness": fresh, "confidence": conf, "single_news_alpha": single})
    noise = sum(x["single_news_alpha"] for x in events if x["event_type"] == "market_noise")
    noise = max(-2.0, min(2.0, noise))
    core = sum(x["single_news_alpha"] for x in events if x["event_type"] != "market_noise")
    raw = core + noise
    if any(x["event_type"] in {"risk_event", "litigation"} and x["impact_direction"] == "negative" for x in events):
        raw = min(raw - 3.0, -8.0 if raw < -8 else raw)
    conf = sum(x["confidence"] for x in events) / len(events)
    cap = 3 if conf < 0.3 else 10
    adj = max(-cap, min(cap, raw))
    return {"news_alpha_adjustment": float(adj), "top_news_events": events, "news_alpha_summary": f"events={len(events)} core={core:.2f} noise={noise:.2f}", "confidence": float(conf), "risk_flags": ["risk_event"] if any(x["event_type"] in {"risk_event", "litigation"} for x in events) else []}
