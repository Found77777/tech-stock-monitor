from __future__ import annotations


def regime_bucket_performance(records: list[dict], regime: str) -> float:
    vals = [float(r.get("alpha", 0)) for r in records if r.get("regime") == regime]
    return float(sum(vals) / len(vals)) if vals else 0.0
