from app.scoring.score_engine import compute_score
from app.signals.signal_engine import generate_signals


def test_signal_generation():
    row = {"code":"600000","name":"测试半导体","new_20d_high":True,"volume_ratio_5d":1.6,"distance_to_ma20":0.02,"distance_to_ma60":0.01,"excess_return_5d":0.01,"excess_return_20d":0.02,"is_liquid":True}
    sig = generate_signals(row)
    assert any(x["signal_name"] == "volume_breakout" for x in sig)


def test_compute_score():
    s = compute_score({"distance_to_ma20":0.02,"distance_to_ma60":0.01,"stock_return_20d":0.08,"relative_strength_score":20,"liquidity_score":70,"drawdown_from_120d_high":-0.1,"volatility_20d":0.02,"is_liquid":True})
    assert 0 <= s["total_score"] <= 100
