from __future__ import annotations

import math


def calculate_mock_score(momentum: float, liquidity: float, relative_strength: float) -> float:
    raw = momentum * 0.4 + liquidity * 0.3 + relative_strength * 0.3
    return max(0.0, min(100.0, raw))


def _safe(v, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return max(lo, min(hi, x))


def _fundamental_score(q: str | None) -> float:
    m = {"strong": 85, "medium": 65, "weak": 35}
    return _safe(m.get(str(q).lower(), 50))


def _policy_score(theme: str | None) -> float:
    t = (theme or "").lower()
    core = ["信创", "半导体设备", "半导体材料", "工业软件", "机器人", "算力基础设施", "数据中心", "网络安全", "数据要素", "智能制造", "高端制造"]
    support = ["国产替代", "工业升级", "数字经济"]
    indirect = ["间接受益", "相关"]
    if any(k.lower() in t for k in core):
        return 88
    if any(k.lower() in t for k in support):
        return 75
    if any(k.lower() in t for k in indirect):
        return 55
    return 40


def _concept_penalty(purity: str | None) -> float:
    m = {"core": 0, "related": 5, "weak": 15, "hype": 30}
    return _safe(m.get(str(purity).lower(), 10))


def compute_score(row: dict) -> dict:
    reasons = []
    dd = _safe(row.get("drawdown_from_120d_high", None), -1000, 1000)
    # low position: sweet spot -50%~-20%
    if row.get("drawdown_from_120d_high") is None:
        low_position = 0
        reasons.append("低位状态：历史区间不足，位置分暂记为0")
    elif -0.5 <= dd <= -0.2:
        low_position = 85
        reasons.append("低位状态：处于-20%~-50%回撤区间，具备修复空间")
    elif dd > -0.1:
        low_position = 30
        reasons.append("低位状态：接近阶段高位，低位优势不足")
    elif dd < -0.6:
        low_position = 25
        reasons.append("低位状态：过度低位且修复不足")
    else:
        low_position = 55
        reasons.append("低位状态：位置中性")

    d20 = _safe(row.get("distance_to_ma20", 0), -10, 10)
    d60 = _safe(row.get("distance_to_ma60", 0), -10, 10)
    r5 = _safe(row.get("stock_return_5d", 0), -10, 10)
    trend = 40
    if d20 > 0:
        trend += 20
    if 0 <= d20 <= 0.08:
        trend += 20
    if d20 > 0.12:
        trend -= 15
    if r5 > 0:
        trend += 10
    if d20 > 0 and d60 > 0:
        trend += 10
    trend = _safe(trend)

    ar5 = row.get("amount_ratio_5d", None)
    if ar5 is None:
        ar5 = row.get("main_net_inflow_5d", None)
    if ar5 is None:
        ar5 = row.get("main_net_inflow_10d", None)
    ar5 = _safe(ar5, -10, 100)
    if ar5 < 1:
        cap = 30
    elif 1.1 <= ar5 <= 2.5:
        cap = 85
    elif ar5 > 3.5:
        cap = 50
    else:
        cap = 60

    fundamental = _fundamental_score(row.get("fundamental_quality"))
    theme = row.get("policy_theme") or row.get("theme")
    policy = _policy_score(theme)
    concept_penalty = _concept_penalty(row.get("concept_purity"))

    overheat = 0
    r20 = _safe(row.get("stock_return_20d", 0), -10, 10)
    if r5 > 0.15: overheat += 10
    if r20 > 0.30: overheat += 15
    if d20 > 0.12: overheat += 10
    if d60 > 0.20: overheat += 15
    if dd > -0.10: overheat += 10
    if _safe(row.get("amount_ratio_5d", 0), -10, 100) > 3.5: overheat += 10
    overheat = _safe(overheat)

    liquidity = _safe(row.get("liquidity_score", 0))
    total = (0.25 * _safe(low_position) + 0.20 * _safe(fundamental) + 0.20 * _safe(policy) +
             0.15 * _safe(cap) + 0.10 * _safe(trend) + 0.10 * _safe(liquidity) -
             _safe(concept_penalty) - _safe(overheat))
    total = _safe(total)

    reasons.extend([
        f"基本面：{row.get('fundamental_quality', 'missing')}（{fundamental:.0f}分）",
        f"政策主题：{theme if theme else '缺失'}（{policy:.0f}分）",
        f"概念纯度：{row.get('concept_purity', 'missing')}（惩罚{concept_penalty:.0f}）",
        f"资金/量能：amount_ratio_5d={row.get('amount_ratio_5d', 'NA')}（{cap:.0f}分）",
        f"风险提示：过热惩罚{overheat:.0f}",
    ])

    # db compatibility mapping
    return {
        "total_score": round(total, 2),
        "trend_score": round(_safe(trend), 2),  # trend_reversal_score
        "momentum_score": round(_safe(cap), 2),  # capital_inflow_score
        "relative_strength_score": round(_safe(policy), 2),  # policy_alignment_score
        "liquidity_score": round(_safe(liquidity), 2),
        "position_score": round(_safe(low_position), 2),  # low_position_score
        "risk_penalty": round(_safe(concept_penalty + overheat), 2),
        "reasons": reasons,
    }
