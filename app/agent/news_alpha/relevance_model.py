from __future__ import annotations


def relevance_score(text: str, stock_meta: dict) -> float:
    text = (text or "").lower()
    score = 0.0
    code = str(stock_meta.get("code", "")).lower()
    name = str(stock_meta.get("name", "")).lower()
    if code and code in text:
        score = max(score, 95)
    if name and name in text:
        score = max(score, 92)
    for k in ["sector", "theme", "policy_theme", "primary_theme", "secondary_theme"]:
        v = str(stock_meta.get(k, "")).lower()
        if v and v in text:
            score += 15
    return float(max(0.0, min(100.0, score if score else 20.0)))
