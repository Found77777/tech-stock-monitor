from app.scoring.score_engine import calculate_mock_score, compute_score


def test_calculate_mock_score_bounds():
    score = calculate_mock_score(momentum=120, liquidity=80, relative_strength=100)
    assert score == 100.0


def test_calculate_mock_score_regular():
    score = calculate_mock_score(momentum=50, liquidity=60, relative_strength=70)
    assert round(score, 2) == 59.0


def test_low_position_recovery_scores_higher():
    low = compute_score({"drawdown_from_120d_high": -0.3, "distance_to_ma20": 0.03, "distance_to_ma60": 0.01, "stock_return_5d": 0.03, "amount_ratio_5d": 1.5, "liquidity_score": 70, "fundamental_quality": "medium", "theme": "工业软件", "concept_purity": "core"})
    high = compute_score({"drawdown_from_120d_high": -0.05, "distance_to_ma20": 0.14, "distance_to_ma60": 0.22, "stock_return_5d": 0.18, "stock_return_20d": 0.35, "amount_ratio_5d": 4.0, "liquidity_score": 70, "fundamental_quality": "medium", "theme": "工业软件", "concept_purity": "core"})
    assert low["total_score"] > high["total_score"]


def test_hype_penalty_and_fundamental_gap():
    strong = compute_score({"drawdown_from_120d_high": -0.3, "amount_ratio_5d": 1.5, "liquidity_score": 60, "fundamental_quality": "strong", "theme": "信创", "concept_purity": "core"})
    weak_hype = compute_score({"drawdown_from_120d_high": -0.3, "amount_ratio_5d": 1.5, "liquidity_score": 60, "fundamental_quality": "weak", "theme": "信创", "concept_purity": "hype"})
    assert strong["total_score"] > weak_hype["total_score"]


def test_total_score_never_nan():
    s = compute_score({"drawdown_from_120d_high": None, "stock_return_5d": None, "stock_return_20d": None, "amount_ratio_5d": None, "distance_to_ma20": None, "distance_to_ma60": None, "liquidity_score": None})
    assert s["total_score"] == s["total_score"]


def test_capital_flow_score_prefers_sustained_inflow():
    sustained = compute_score({
        "drawdown_from_120d_high": -0.3,
        "distance_to_ma20": 0.02,
        "distance_to_ma60": 0.03,
        "net_inflow_1d": 1e7,
        "net_inflow_5d": 5e7,
        "net_inflow_10d": 1.2e8,
        "amount_ratio_5d": 1.5,
        "volume_ratio_5d": 1.4,
        "price_volume_resonance": 1,
        "liquidity_score": 60,
    })
    pulse = compute_score({
        "drawdown_from_120d_high": -0.3,
        "distance_to_ma20": 0.02,
        "distance_to_ma60": 0.03,
        "net_inflow_1d": 2e7,
        "net_inflow_5d": -1e7,
        "net_inflow_10d": -2e7,
        "amount_ratio_5d": 1.0,
        "volume_ratio_5d": 0.9,
        "price_volume_resonance": 0,
        "liquidity_score": 60,
    })
    assert sustained["momentum_score"] > pulse["momentum_score"]


def test_low_position_score_uses_structure_not_only_drawdown():
    better = compute_score({
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.28,
        "percentile_250d": 0.35,
        "consolidation_days": 12,
        "ma_structure_score": 75,
        "trend_reversal_score": 70,
        "liquidity_score": 50,
    })
    worse = compute_score({
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.28,
        "percentile_250d": 0.92,
        "consolidation_days": 1,
        "ma_structure_score": 20,
        "trend_reversal_score": 20,
        "liquidity_score": 50,
    })
    assert better["position_score"] > worse["position_score"]


def test_metadata_missing_reduces_score():
    rich = compute_score({
        "drawdown_from_120d_high": -0.25,
        "drawdown_from_250d_high": -0.3,
        "percentile_250d": 0.35,
        "consolidation_days": 10,
        "ma_structure_score": 70,
        "amount_ratio_5d": 1.4,
        "fundamental_quality": "strong",
        "policy_theme": "信创",
        "concept_purity": "core",
    })
    missing = compute_score({
        "drawdown_from_120d_high": -0.25,
        "drawdown_from_250d_high": -0.3,
        "percentile_250d": 0.35,
        "consolidation_days": 10,
        "ma_structure_score": 70,
        "amount_ratio_5d": None,
    })
    assert rich["total_score"] > missing["total_score"]


def test_volume_down_fall_not_high_score():
    down = compute_score({
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.25,
        "percentile_250d": 0.3,
        "consolidation_days": 8,
        "ma_structure_score": 60,
        "distance_to_ma20": -0.05,
        "distance_to_ma60": -0.08,
        "amount_ratio_5d": 1.8,
        "volume_ratio_5d": 1.6,
        "price_volume_resonance": -1,
    })
    up = compute_score({
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.25,
        "percentile_250d": 0.3,
        "consolidation_days": 8,
        "ma_structure_score": 60,
        "distance_to_ma20": 0.02,
        "distance_to_ma60": 0.03,
        "amount_ratio_5d": 1.8,
        "volume_ratio_5d": 1.6,
        "price_volume_resonance": 1,
    })
    assert up["momentum_score"] > down["momentum_score"]


def test_pure_downtrend_low_position_not_high():
    s = compute_score({
        "drawdown_from_120d_high": -0.55,
        "drawdown_from_250d_high": -0.7,
        "percentile_250d": 0.05,
        "consolidation_days": 0,
        "ma_structure_score": 20,
        "distance_to_ma20": -0.12,
        "distance_to_ma60": -0.18,
    })
    assert s["position_score"] < 40


def test_fake_rebound_gets_penalized():
    fake = compute_score({
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.3,
        "percentile_250d": 0.25,
        "consolidation_days": 8,
        "distance_to_ma20": -0.03,
        "distance_to_ma60": -0.06,
        "ma60_slope": -0.005,
        "ma120_slope": -0.003,
        "price_volume_resonance": -1,
        "amount_ratio_5d": 1.2,
        "volume_ratio_5d": 1.3,
    })
    good = compute_score({
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.3,
        "percentile_250d": 0.25,
        "consolidation_days": 12,
        "distance_to_ma20": 0.01,
        "distance_to_ma60": 0.02,
        "ma20_slope": 0.002,
        "ma60_slope": 0.001,
        "price_volume_resonance": 1,
        "amount_ratio_5d": 1.4,
        "volume_ratio_5d": 1.3,
    })
    assert good["total_score"] > fake["total_score"]


def _risk_reason(result: dict) -> str:
    return next(x for x in result["reasons"] if x.startswith("风险惩罚："))


def test_risk_penalty_matches_breakdown_and_total_formula():
    row = {
        "trend_reversal_score": 85,
        "net_inflow_1d": 1e7,
        "net_inflow_5d": 5e7,
        "net_inflow_10d": 1e8,
        "amount_ratio_5d": 4.2,
        "volume_ratio_5d": 1.5,
        "price_volume_resonance": 1,
        "liquidity_score": 80,
        "drawdown_from_120d_high": -0.05,
        "drawdown_from_250d_high": -0.25,
        "percentile_250d": 35,
        "consolidation_days": 12,
        "ma_structure_score": 70,
        "distance_to_ma20": 0.15,
        "distance_to_ma60": 0.25,
        "stock_return_5d": 0.2,
        "stock_return_20d": 0.35,
        "fundamental_quality": "medium",
        "theme": "信创",
        "policy_theme": "信创",
        "concept_purity": "hype",
        "_ai_analysis": {"ai_risk_flags": ["监管", "减持", "诉讼"]},
    }
    result = compute_score(row)
    reason = _risk_reason(result)
    assert "概念纯度扣15" in reason
    assert "过热扣10" in reason
    assert "数据缺失扣0" in reason
    assert "AI风险扣10" in reason
    assert result["risk_penalty"] == 30
    base_score = (
        0.25 * result["trend_score"]
        + 0.20 * result["momentum_score"]
        + 0.20 * result["relative_strength_score"]
        + 0.15 * result["liquidity_score"]
        + 0.20 * result["position_score"]
    )
    assert abs(result["total_score"] - max(0, min(100, base_score - result["risk_penalty"]))) <= 0.05


def test_turnover_missing_and_estimated_amount_do_not_create_missing_penalty():
    result = compute_score({
        "amount": 100_000_000,
        "volume": 1000,
        "amount_estimated": True,
        "avg_amount_20d": 100_000_000,
        "avg_turnover_20d": None,
        "amount_ratio_5d": None,
        "liquidity_score": 80,
        "fundamental_quality": "medium",
        "theme": "信创",
        "policy_theme": "信创",
        "concept_purity": "core",
    })
    assert "数据缺失扣0" in _risk_reason(result)
    assert result["risk_penalty"] <= 10


def test_high_component_scores_are_not_silently_collapsed_to_zero():
    result = compute_score({
        "trend_reversal_score": 100,
        "net_inflow_1d": 1e8,
        "net_inflow_5d": 5e8,
        "net_inflow_10d": 8e8,
        "amount_ratio_5d": 1.5,
        "volume_ratio_5d": 1.4,
        "price_volume_resonance": 1,
        "liquidity_score": 80,
        "drawdown_from_120d_high": -0.2,
        "drawdown_from_250d_high": -0.3,
        "percentile_250d": 45,
        "consolidation_days": 10,
        "ma_structure_score": 50,
        "fundamental_quality": "medium",
        "theme": "弱相关概念",
        "policy_theme": "弱相关概念",
        "concept_purity": "hype",
    })
    assert result["trend_score"] >= 90
    assert result["momentum_score"] >= 80
    assert result["liquidity_score"] == 80
    assert result["risk_penalty"] <= 30
    assert result["total_score"] > 25
