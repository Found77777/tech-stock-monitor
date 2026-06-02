from __future__ import annotations

from dataclasses import dataclass

from .breadth_metrics import compute_breadth
from .liquidity_metrics import compute_liquidity_regime
from .policy_sentiment_metrics import compute_policy_intensity
from .volatility_metrics import compute_volatility_regime


@dataclass
class RegimeWeightModel:
    mode: str = "rule_default"

    def get_weights(self, regime_probs: dict[str, float]) -> dict[str, float]:
        base = {
            "bull_trend": 0.35,
            "high_volatility": -0.25,
            "policy_driven": 0.15,
            "liquidity_rich": 0.20,
        }
        # hook for learned calibration
        return {k: base.get(k, 0.0) * float(regime_probs.get(k, 0.0)) for k in regime_probs}


class MarketRegimeEngine:
    def __init__(self, weight_model: RegimeWeightModel | None = None):
        self.weight_model = weight_model or RegimeWeightModel()

    def evaluate(self, market_stats: dict, news_stats: dict | None = None) -> dict:
        news_stats = news_stats or {}
        breadth = compute_breadth(market_stats)
        vol = compute_volatility_regime(market_stats)
        liq = compute_liquidity_regime(market_stats)
        policy = compute_policy_intensity(news_stats)

        bull_trend = min(1.0, max(0.0, 0.4 * breadth.pct_above_ma20 + 0.4 * breadth.pct_above_ma60 + 0.2 * min(1.5, breadth.adv_decl_ratio) / 1.5))
        probs = {
            "bull_trend": round(bull_trend, 4),
            "high_volatility": vol["high_volatility_prob"],
            "policy_driven": policy["policy_driven_prob"],
            "liquidity_rich": liq["liquidity_rich_prob"],
        }
        weights = self.weight_model.get_weights(probs)
        composite_regime_bias = round(sum(weights.values()), 4)
        return {
            "regime_probabilities": probs,
            "regime_weights": weights,
            "composite_regime_bias": composite_regime_bias,
            "explain": {
                "breadth": breadth.__dict__,
                "volatility": vol,
                "liquidity": liq,
                "policy": policy,
            },
        }
