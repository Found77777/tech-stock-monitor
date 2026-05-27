from app.agent.news_alpha.alpha_aggregator import aggregate_news_alpha
from app.confidence.unified_confidence import calibrate_confidence, uncertainty_band
from app.explainability.alpha_attribution import score_waterfall
from app.regime.market_regime_engine import MarketRegimeEngine


def test_regime_probabilities_nonexclusive():
    engine = MarketRegimeEngine()
    out = engine.evaluate(
        {"advancers": 2200, "decliners": 1800, "pct_above_ma20": 0.62, "pct_above_ma60": 0.55, "new_high_low_ratio": 1.2, "realized_vol": 0.28, "turnover_z": 0.7, "spread_bps": 9},
        {"policy_hits": 3, "total_news": 8},
    )
    probs = out["regime_probabilities"]
    assert 0 <= probs["bull_trend"] <= 1
    assert 0 <= probs["high_volatility"] <= 1
    assert 0 <= probs["policy_driven"] <= 1


def test_news_alpha_market_noise_capped():
    items = [{"title": "板块异动 短线情绪", "summary": "", "publish_time": "2026-05-27"} for _ in range(5)]
    out = aggregate_news_alpha(items, {"code": "002465", "name": "海格通信"})
    assert out["news_alpha_adjustment"] <= 2


def test_confidence_and_uncertainty_band():
    c = calibrate_confidence(0.8, 0.7, 0.6, 0.9)
    lo, hi = uncertainty_band(3.5, c)
    assert 0 <= c <= 1
    assert lo < hi


def test_score_waterfall_consistency():
    w = score_waterfall(42, 3, -4, 5, 6)
    assert w["final_score"] == 40
