from __future__ import annotations


def calculate_mock_score(momentum: float, liquidity: float, relative_strength: float) -> float:
    raw = momentum * 0.4 + liquidity * 0.3 + relative_strength * 0.3
    return max(0.0, min(100.0, raw))


def compute_score(row: dict) -> dict:
    trend = (max(min((row.get("distance_to_ma20", 0) + row.get("distance_to_ma60", 0)) * 200, 100), 0))
    momentum = max(min(row.get("stock_return_20d", 0) * 300 + 50, 100), 0)
    rs = max(min(row.get("relative_strength_score", 0) * 0.8 + 50, 100), 0)
    liq = max(min(row.get("liquidity_score", 0), 100), 0)
    position = max(min((1 + row.get("drawdown_from_120d_high", -0.5)) * 100, 100), 0)
    risk = 0
    reasons = []
    if row.get("volatility_20d", 0) > 0.04:
        risk += 8
        reasons.append("波动率偏高")
    if row.get("distance_to_ma20", 0) > 0.15:
        risk += 10
        reasons.append("偏离MA20较大")
    if not row.get("is_liquid", True):
        risk += 12
        reasons.append("流动性不足")
    total = 0.3*trend + 0.2*momentum + 0.2*rs + 0.15*liq + 0.15*position - risk
    reasons.append(f"趋势{trend:.1f}/动量{momentum:.1f}/相对强弱{rs:.1f}")
    return {
        "total_score": round(max(min(total,100),0),2),
        "trend_score": round(trend,2),
        "momentum_score": round(momentum,2),
        "relative_strength_score": round(rs,2),
        "liquidity_score": round(liq,2),
        "position_score": round(position,2),
        "risk_penalty": round(risk,2),
        "reasons": reasons,
    }
