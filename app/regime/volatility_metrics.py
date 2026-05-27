from __future__ import annotations


def compute_volatility_regime(market_stats: dict) -> dict:
    realized_vol = float(market_stats.get("realized_vol", 0.2) or 0.2)
    vol_of_vol = float(market_stats.get("vol_of_vol", 0.1) or 0.1)
    high_vol = min(1.0, max(0.0, (realized_vol - 0.18) / 0.2 + 0.5))
    return {"realized_vol": realized_vol, "vol_of_vol": vol_of_vol, "high_volatility_prob": round(high_vol, 4)}
