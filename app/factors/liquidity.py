import pandas as pd


def add_liquidity_factors(df: pd.DataFrame, min_avg_amount: float = 30_000_000) -> pd.DataFrame:
    d = df.sort_values("trade_date").copy()
    amount = pd.to_numeric(d.get("amount"), errors="coerce")
    volume = pd.to_numeric(d.get("volume"), errors="coerce")
    turnover = pd.to_numeric(d.get("turnover_rate"), errors="coerce")
    d["avg_amount_20d"] = amount.rolling(20, min_periods=1).mean()
    d["avg_turnover_20d"] = turnover.rolling(20, min_periods=1).mean()

    amount_score = (d["avg_amount_20d"] / max(float(min_avg_amount), 1.0) * 60).clip(0, 100)
    turnover_score = (d["avg_turnover_20d"] / 5.0 * 40).clip(0, 40)
    turnover_missing = d["avg_turnover_20d"].isna()
    d["liquidity_score"] = (amount_score + turnover_score.fillna(0)).clip(0, 100)
    # Turnover is useful but optional: a liquid amount alone should not collapse to zero.
    d.loc[turnover_missing & d["avg_amount_20d"].notna(), "liquidity_score"] = amount_score[turnover_missing & d["avg_amount_20d"].notna()].clip(0, 80)
    d.loc[d["avg_amount_20d"].isna() & volume.isna(), "liquidity_score"] = 0
    d["liquidity_score"] = d["liquidity_score"].fillna(0)
    d["is_liquid"] = d["avg_amount_20d"] >= min_avg_amount
    return d
