from app.scoring.score_engine import calculate_mock_score, compute_score


def test_calculate_mock_score_bounds():
    score = calculate_mock_score(momentum=120, liquidity=80, relative_strength=100)
    assert score == 100.0


def test_calculate_mock_score_regular():
    score = calculate_mock_score(momentum=50, liquidity=60, relative_strength=70)
    assert round(score, 2) == 59.0


def test_position_score_missing_not_nan():
    s = compute_score({"drawdown_from_120d_high": None, "distance_to_ma20": 0, "distance_to_ma60": 0, "stock_return_20d": 0, "relative_strength_score": 0, "liquidity_score": 0, "volatility_20d": 0, "is_liquid": True})
    assert s["position_score"] == 0
    assert s["total_score"] >= 0
    assert any("历史区间不足" in x for x in s["reasons"])
