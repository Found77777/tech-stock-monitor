import pandas as pd


def add_technical_factors(df: pd.DataFrame) -> pd.DataFrame:
    d = df.sort_values("trade_date").copy()
    d["pct_change"] = d["close"].pct_change().fillna(0)
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma60"] = d["close"].rolling(60).mean()
    d["ma120"] = d["close"].rolling(120).mean()
    d["ma20_prev"] = d["ma20"].shift(1)
    d["ma60_prev"] = d["ma60"].shift(1)
    d["ma120_prev"] = d["ma120"].shift(1)
    d["distance_to_ma20"] = (d["close"] - d["ma20"]) / d["ma20"]
    d["distance_to_ma60"] = (d["close"] - d["ma60"]) / d["ma60"]
    d["ma20_slope"] = (d["ma20"] - d["ma20_prev"]) / d["ma20_prev"].replace(0, pd.NA)
    d["ma60_slope"] = (d["ma60"] - d["ma60_prev"]) / d["ma60_prev"].replace(0, pd.NA)
    d["ma120_slope"] = (d["ma120"] - d["ma120_prev"]) / d["ma120_prev"].replace(0, pd.NA)
    d["new_20d_high"] = d["close"] >= d["close"].rolling(20).max()
    d["drawdown_from_120d_high"] = d["close"] / d["close"].rolling(120).max() - 1
    d["drawdown_from_250d_high"] = d["close"] / d["close"].rolling(250).max() - 1

    roll_250_high = d["close"].rolling(250).max()
    roll_250_low = d["close"].rolling(250).min()
    denom = (roll_250_high - roll_250_low)
    d["percentile_250d_flat_range"] = denom.fillna(0) == 0
    denom_safe = denom.replace(0, pd.NA)
    d["percentile_250d"] = (((d["close"] - roll_250_low) / denom_safe) * 100).fillna(50).clip(0, 100)

    d["volatility_20d"] = d["close"].pct_change().rolling(20).std()
    d["volume_ratio_5d"] = d["volume"].rolling(5).mean() / d["volume"].rolling(20).mean()
    d["amount_ratio_5d"] = d["amount"].rolling(5).mean() / d["amount"].rolling(20).mean()

    # Capital-flow proxies (if real net-inflow not available from source).
    # TODO: replace with source native main-net-inflow fields when stable API exists.
    d["net_inflow_1d"] = (d["pct_change"] * d["amount"]).fillna(0)
    d["net_inflow_5d"] = d["net_inflow_1d"].rolling(5).sum().fillna(0)
    d["net_inflow_10d"] = d["net_inflow_1d"].rolling(10).sum().fillna(0)

    # price_volume_resonance: up+vol => positive, down+vol => negative, up+shrink => mild positive.
    vol_delta = d["volume"].pct_change().fillna(0)
    d["price_volume_resonance"] = 0.0
    d.loc[(d["pct_change"] > 0) & (vol_delta > 0), "price_volume_resonance"] = 1.0
    d.loc[(d["pct_change"] > 0) & (vol_delta <= 0), "price_volume_resonance"] = 0.5
    d.loc[(d["pct_change"] < 0) & (vol_delta > 0), "price_volume_resonance"] = -1.0

    # Consolidation: low vol + narrow range.
    range_20 = d["close"].rolling(20).max() / d["close"].rolling(20).min().replace(0, pd.NA) - 1
    is_consolidating = (d["volatility_20d"] <= d["volatility_20d"].rolling(60).quantile(0.4)) & (range_20 <= 0.18)
    d["consolidation_days"] = is_consolidating.fillna(False).astype(int).rolling(20).sum()

    # MA structure score.
    d["ma_structure_score"] = 40.0
    d.loc[(d["ma20"] > d["ma60"]) & (d["ma60"] > d["ma120"]), "ma_structure_score"] += 20  # 高位趋势
    ma20_cross_up = (d["ma20"] > d["ma60"]) & (d["ma20_prev"] <= d["ma60_prev"]) 
    d.loc[ma20_cross_up, "ma_structure_score"] += 20  # MA20上穿MA60
    ma60_flat = (d["ma60"] - d["ma60_prev"]).abs() / d["ma60"].replace(0, pd.NA) <= 0.003
    d.loc[ma60_flat.fillna(False), "ma_structure_score"] += 10  # MA60走平
    ma120_down_div = (d["ma120"] < d["ma120_prev"]) & ((d["ma60"] - d["ma120"]) / d["ma120"].replace(0, pd.NA) > 0.08)
    d.loc[ma120_down_div.fillna(False), "ma_structure_score"] -= 15  # MA120向下发散
    d["ma_structure_score"] = d["ma_structure_score"].clip(0, 100).fillna(0)

    # Trend reversal score.
    platform_breakout = d["close"] > d["close"].rolling(20).max().shift(1)
    bottom_lift = d["close"].rolling(10).min() > d["close"].rolling(20).min().shift(5)
    vol_boost = d["volume_ratio_5d"] > 1.2
    d["trend_reversal_score"] = 20.0
    d.loc[vol_boost.fillna(False), "trend_reversal_score"] += 20
    d.loc[ma20_cross_up.fillna(False), "trend_reversal_score"] += 25
    d.loc[bottom_lift.fillna(False), "trend_reversal_score"] += 20
    d.loc[platform_breakout.fillna(False), "trend_reversal_score"] += 25
    d["trend_reversal_score"] = d["trend_reversal_score"].clip(0, 100).fillna(0)

    return d
