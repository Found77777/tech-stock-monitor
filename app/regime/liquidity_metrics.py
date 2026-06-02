from __future__ import annotations


def compute_liquidity_regime(market_stats: dict) -> dict:
    turnover_z = float(market_stats.get("turnover_z", 0) or 0)
    spread_bps = float(market_stats.get("spread_bps", 8) or 8)
    prob = min(1.0, max(0.0, 0.5 + 0.2 * turnover_z - 0.02 * (spread_bps - 8)))
    return {
        "turnover_z": turnover_z,
        "spread_bps": spread_bps,
        "liquidity_rich_prob": round(prob, 4),
    }
