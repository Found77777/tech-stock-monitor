from __future__ import annotations

import math
from app.themes.theme_scoring import evaluate_theme


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


def _capital_flow_score(row: dict) -> tuple[float, str]:
    n1 = _safe(row.get("net_inflow_1d"), -1e12, 1e12)
    n5 = _safe(row.get("net_inflow_5d"), -1e12, 1e12)
    n10 = _safe(row.get("net_inflow_10d"), -1e12, 1e12)
    ar5 = _safe(row.get("amount_ratio_5d"), 0, 10)
    vr5 = _safe(row.get("volume_ratio_5d"), 0, 10)
    pvr = _safe(row.get("price_volume_resonance"), -1, 1)
    d20 = _safe(row.get("distance_to_ma20"), -10, 10)
    d60 = _safe(row.get("distance_to_ma60"), -10, 10)

    score = 30.0
    if n10 > 0:
        score += 25
    elif n5 > 0:
        score += 15
    elif n1 > 0:
        score += 5
    else:
        score -= 10

    if ar5 == 0:
        score -= 10
    elif 1.1 <= ar5 <= 2.5:
        score += 15
    elif ar5 < 1:
        score -= 5
    elif ar5 > 3.5:
        score -= 5

    if vr5 >= 1.2:
        score += 8
    elif vr5 < 0.9:
        score -= 3

    if pvr > 0.8:
        score += 12
    elif pvr > 0:
        score += 6
    elif pvr < -0.8:
        score -= 12

    # volume-price structure
    if d60 > 0 and vr5 > 1.2 and pvr >= 0.5:
        score += 10  # 放量突破MA60
    if d20 < 0 and vr5 > 1.2:
        score -= 12  # 放量跌破MA20
    if pvr < -0.5 and vr5 > 1.1:
        score -= 10  # 放量下跌额外扣分

    reason = f"主力净流入(1/5/10日)={n1:.0f}/{n5:.0f}/{n10:.0f}，量比5日={ar5:.2f}，量能比5日={vr5:.2f}，量价共振={pvr:.2f}"
    return _safe(score), reason


def compute_score(row: dict) -> dict:
    reasons = []
    dd120 = _safe(row.get("drawdown_from_120d_high", None), -1000, 1000)
    dd250 = _safe(row.get("drawdown_from_250d_high", None), -1000, 1000)
    pct250 = _safe(row.get("percentile_250d", None), 0, 100)
    pct250_flat_range = bool(row.get("percentile_250d_flat_range", False))
    cons_days = _safe(row.get("consolidation_days", None), 0, 250)
    ma_struct = _safe(row.get("ma_structure_score", None), 0, 100)
    d20 = _safe(row.get("distance_to_ma20", 0), -10, 10)
    d60 = _safe(row.get("distance_to_ma60", 0), -10, 10)

    low_position = 35.0
    # 回撤但不崩坏
    if -0.55 <= dd250 <= -0.15:
        low_position += 20
    elif dd250 < -0.65:
        low_position -= 10
    elif dd250 > -0.1:
        low_position -= 8

    # 250日分位：偏低到中低更优
    if 20 <= pct250 <= 50:
        low_position += 20
    elif pct250 < 10:
        low_position -= 8
    elif pct250 > 75:
        low_position -= 10

    # 横盘充分
    if cons_days >= 10:
        low_position += 15
    elif cons_days >= 5:
        low_position += 8

    # MA结构
    low_position += (ma_struct - 50) * 0.2

    # MA120不崩坏
    if dd120 < -0.45:
        low_position -= 12
    # 纯下跌/破位过滤
    if d20 < -0.08 and d60 < -0.12:
        low_position -= 25
        reasons.append("低位风险：均线下方深度运行，疑似纯下跌趋势")

    low_position = _safe(low_position)
    if pct250 >= 80:
        pos_label = "接近250日高点"
    elif pct250 <= 20:
        pos_label = "接近250日低位"
    else:
        pos_label = "中位区间"
    extra = "；区间不足(250日高低点重合，分位按50处理)" if pct250_flat_range else ""
    reasons.append(
        f"低位状态：250日回撤={dd250:.2%}，250日分位={pct250:.1f}%（{pos_label}），横盘{int(cons_days)}天，MA结构={ma_struct:.0f}{extra}"
    )

    r5 = _safe(row.get("stock_return_5d", 0), -10, 10)
    trend = _safe(row.get("trend_reversal_score", 40))
    ma20_slope = _safe(row.get("ma20_slope", 0), -1, 1)
    ma60_slope = _safe(row.get("ma60_slope", 0), -1, 1)
    ma120_slope = _safe(row.get("ma120_slope", 0), -1, 1)
    if trend == 40:
        # fallback when factor not available
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
    if ma20_slope > 0:
        trend += 8
    if ma60_slope > 0:
        trend += 8
    if d20 > 0:
        trend += 8
    if row.get("ma20") is not None and row.get("ma60") is not None and row.get("ma20") > row.get("ma60"):
        trend += 8
    if _safe(row.get("amount_ratio_5d", 0), 0, 10) > 1.2 and _safe(row.get("volume_ratio_5d", 0), 0, 10) > 1.1:
        trend += 6

    if _safe(row.get("consolidation_days", 0), 0, 250) >= 10 and _safe(row.get("volatility_20d", 1), 0, 10) < 0.03 and _safe(row.get("price_volume_resonance", 0), -1, 1) > 0.5:
        trend += 15
        reasons.append("横盘突破：横盘充分且波动收敛后放量突破")
    trend = _safe(trend)

    # recent strength
    r10 = _safe(row.get("stock_return_10d", 0), -10, 10)
    rr = _safe(row.get("relative_return_vs_sector", row.get("excess_return_5d", 0)), -10, 10)
    recent_strength = _safe(50 + r5 * 120 + r10 * 80 + rr * 120)

    cap, cap_reason = _capital_flow_score(row)

    fq = row.get("fundamental_quality")
    fundamental = _fundamental_score(fq)
    theme_eval = evaluate_theme(row)
    theme = theme_eval.get("primary_theme") or row.get("policy_theme") or row.get("theme")
    policy = _safe(theme_eval.get("policy_alignment_score", _policy_score(theme)))
    concept_penalty = _safe(max(0.0, 100 - theme_eval.get("purity_score", 50)) / 4)
    missing_penalty = 0.0
    if not fq:
        missing_penalty += 6
        reasons.append("数据缺失风险：fundamental_quality 缺失")
    if not row.get("policy_theme") and not row.get("theme"):
        missing_penalty += 4
        reasons.append("数据缺失风险：policy/theme 标签缺失")
    if row.get("amount_ratio_5d") is None:
        missing_penalty += 5
        reasons.append("资金流 proxy 风险：amount_ratio_5d 缺失")

    overheat = 0
    r20 = _safe(row.get("stock_return_20d", 0), -10, 10)
    if r5 > 0.15: overheat += 10
    if r20 > 0.30: overheat += 15
    if d20 > 0.12: overheat += 10
    if d60 > 0.20: overheat += 15
    if dd120 > -0.10: overheat += 10
    if _safe(row.get("amount_ratio_5d", 0), -10, 100) > 3.5: overheat += 10
    overheat = _safe(overheat)

    liquidity = _safe(row.get("liquidity_score", 0))
    # --- AI Agent sentiment integration ---
    ai_data = row.get("_ai_analysis", {})
    ai_sentiment = _safe(ai_data.get("ai_sentiment_score", 50), 0, 100)
    ai_confidence = _safe(ai_data.get("ai_confidence", 0), 0, 100)
    ai_policy_boost = _safe(ai_data.get("ai_policy_boost", 0), -15, 15)
    ai_fundamental_boost = _safe(ai_data.get("ai_fundamental_boost", 0), -10, 10)
    market_adj = _safe(ai_data.get("market_sentiment_adj", 0), -10, 10)
    tech_adj = _safe(ai_data.get("tech_sector_adj", 0), -10, 10)
    policy = _safe(policy + ai_policy_boost)
    fundamental = _safe(fundamental + ai_fundamental_boost)
    ai_risk_flags = ai_data.get("ai_risk_flags", [])
    ai_risk_penalty = min(len(ai_risk_flags) * 5, 15) if isinstance(ai_risk_flags, list) else 0.0
    ai_reasons = ai_data.get("ai_reasons", [])
    if isinstance(ai_reasons, list):
        reasons.extend(ai_reasons)
    # fake rebound filter
    fake_rebound = (ma60_slope < -0.002 and ma120_slope < -0.001 and d20 < 0 and _safe(row.get("price_volume_resonance", 0), -1, 1) < 0)
    if fake_rebound:
        overheat += 20
        trend = _safe(trend - 20)
        reasons.append("假反弹风险：MA60/MA120仍下行且股价未站上MA20，量价共振为负")

    total = (0.12 * _safe(low_position) + 0.08 * _safe(fundamental) + 0.14 * _safe(policy) +
             0.16 * _safe(cap) + 0.16 * _safe(trend) + 0.08 * _safe(liquidity) + 0.07 * _safe(recent_strength) +
             0.12 * _safe(ai_sentiment) + market_adj + tech_adj -
             _safe(concept_penalty) - _safe(overheat) - _safe(missing_penalty) - _safe(ai_risk_penalty) +
             0.13 * _safe(theme_eval.get("theme_relevance_score", 0)))
    total = _safe(total)

    reasons.extend([
        f"基本面：{row.get('fundamental_quality', 'missing')}（{fundamental:.0f}分）",
        f"主题研究：primary={theme_eval.get('primary_theme','')} secondary={theme_eval.get('secondary_theme','')} strength={theme_eval.get('theme_strength',0):.0f}",
        f"主题相关性：theme_relevance_score={theme_eval.get('theme_relevance_score',0):.0f} 研发={theme_eval.get('research_strength_score',0):.0f} 创新={theme_eval.get('innovation_score',0):.0f} 产业地位={theme_eval.get('industry_position_score',0):.0f}",
        f"政策匹配：{theme if theme else '缺失'}（{policy:.0f}分） 纯度={theme_eval.get('purity_score',0):.0f}（惩罚{concept_penalty:.0f}）",
        f"资金/量能：{cap_reason}（capital_flow_score={cap:.0f}分）",
        f"趋势恢复：trend_reversal_score={trend:.0f}，MA20斜率={ma20_slope:.2%}，MA60斜率={ma60_slope:.2%}",
        f"近期强度：recent_strength_score={recent_strength:.0f}（5日={r5:.2%}，10日={r10:.2%}，相对行业={rr:.2%}）",
        "MA结构恢复：关注 MA20/MA60/MA120 方向一致性",
        f"风险提示：过热惩罚{overheat:.0f}",
        "主题标签静态风险：当前仍以规则与静态元数据为主，需结合财报/专利实证",
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
        "recent_strength_score": round(_safe(recent_strength), 2),
        "reasons": reasons,
    }
