from __future__ import annotations


def backtest_sanity(scores: list[float]) -> dict:
    if not scores:
        return {"mean": 0.0, "std": 0.0}
    m = sum(scores) / len(scores)
    v = sum((x - m) ** 2 for x in scores) / len(scores)
    return {"mean": float(m), "std": float(v ** 0.5)}
