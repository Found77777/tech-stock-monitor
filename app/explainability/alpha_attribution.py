from __future__ import annotations


def score_waterfall(base_score: float, regime_adj: float, capital_flow_adj: float, news_alpha_adj: float, risk_penalty: float) -> dict:
    final_score = base_score + regime_adj + capital_flow_adj + news_alpha_adj - risk_penalty
    return {
        "base_score": base_score,
        "regime_adj": regime_adj,
        "capital_flow_adj": capital_flow_adj,
        "news_alpha_adj": news_alpha_adj,
        "risk_penalty": risk_penalty,
        "final_score": final_score,
    }
