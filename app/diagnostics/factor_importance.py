from __future__ import annotations


def attribution_report(scores: dict[str, float]) -> dict:
    pos = sorted([(k, v) for k, v in scores.items() if v > 0], key=lambda x: x[1], reverse=True)
    neg = sorted([(k, v) for k, v in scores.items() if v < 0], key=lambda x: x[1])
    return {"top_positive": pos[:5], "top_negative": neg[:5]}
