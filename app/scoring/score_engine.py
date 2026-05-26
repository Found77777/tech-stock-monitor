from __future__ import annotations

import math


def calculate_mock_score(momentum: float, liquidity: float, relative_strength: float) -> float:
    raw = momentum * 0.4 + liquidity * 0.3 + relative_strength * 0.3
    return max(0.0, min(100.0, raw))


def _safe_score(v, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def compute_score(row: dict) -> dict:
    trend_raw = (row.get("distance_to_ma20", 0) + row.get("distance_to_ma60", 0)) * 200
    momentum_raw = row.get("stock_return_20d", 0) * 300 + 50
    rs_raw = row.get("relative_strength_score", 0) * 0.8 + 50
    liq_raw = row.get("liquidity_score", 0)

    reasons = []
    dd = row.get("drawdown_from_120d_high", None)
    if dd is None:
        position_raw = 0
        reasons.append("历史区间不足，位置分暂记为0")
    else:
        try:
            ddv = float(dd)
            if math.isnan(ddv) or math.isinf(ddv):
                position_raw = 0
                reasons.append("历史区间不足，位置分暂记为0")
            else:
                position_raw = (1 + ddv) * 100
        except Exception:
            position_raw = 0
            reasons.append("历史区间不足，位置分暂记为0")

    trend = _safe_score(trend_raw)
    momentum = _safe_score(momentum_raw)
    rs = _safe_score(rs_raw)
    liq = _safe_score(liq_raw)
    position = _safe_score(position_raw)

    risk = 0.0
    vol = row.get("volatility_20d", 0)
    d20 = row.get("distance_to_ma20", 0)
    if _safe_score(vol, -1e9, 1e9) > 0.04:
        risk += 8
        reasons.append("波动率偏高")
    if _safe_score(d20, -1e9, 1e9) > 0.15:
        risk += 10
        reasons.append("偏离MA20较大")
    if not row.get("is_liquid", True):
        risk += 12
        reasons.append("流动性不足")
    risk = _safe_score(risk)

    total_raw = 0.3 * trend + 0.2 * momentum + 0.2 * rs + 0.15 * liq + 0.15 * position - risk
    total = _safe_score(total_raw)
    reasons.append(f"趋势{trend:.1f}/动量{momentum:.1f}/相对强弱{rs:.1f}")
    return {
        "total_score": round(total, 2),
        "trend_score": round(trend, 2),
        "momentum_score": round(momentum, 2),
        "relative_strength_score": round(rs, 2),
        "liquidity_score": round(liq, 2),
        "position_score": round(position, 2),
        "risk_penalty": round(risk, 2),
        "reasons": reasons,
    }
