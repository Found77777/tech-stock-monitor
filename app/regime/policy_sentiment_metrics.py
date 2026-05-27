from __future__ import annotations


def compute_policy_intensity(news_stats: dict) -> dict:
    policy_hits = float(news_stats.get("policy_hits", 0) or 0)
    total_news = float(news_stats.get("total_news", 1) or 1)
    intensity = min(1.0, max(0.0, policy_hits / max(total_news, 1.0)))
    return {
        "policy_hits": int(policy_hits),
        "total_news": int(total_news),
        "policy_driven_prob": round(intensity, 4),
    }
