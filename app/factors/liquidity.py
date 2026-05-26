import pandas as pd


def add_liquidity_factors(df: pd.DataFrame, min_avg_amount: float = 30_000_000) -> pd.DataFrame:
    d = df.sort_values("trade_date").copy()
    d["avg_amount_20d"] = d["amount"].rolling(20).mean()
    d["avg_turnover_20d"] = d["turnover_rate"].rolling(20).mean()
    d["liquidity_score"] = ((d["avg_amount_20d"].rank(pct=True) + d["avg_turnover_20d"].rank(pct=True)) / 2 * 100).fillna(0)
    d["is_liquid"] = d["avg_amount_20d"] >= min_avg_amount
    return d
