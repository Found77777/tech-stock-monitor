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
