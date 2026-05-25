import pandas as pd


def add_technical_factors(df: pd.DataFrame) -> pd.DataFrame:
    d = df.sort_values("trade_date").copy()
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma60"] = d["close"].rolling(60).mean()
    d["ma120"] = d["close"].rolling(120).mean()
    d["distance_to_ma20"] = (d["close"] - d["ma20"]) / d["ma20"]
    d["distance_to_ma60"] = (d["close"] - d["ma60"]) / d["ma60"]
    d["new_20d_high"] = d["close"] >= d["close"].rolling(20).max()
    d["drawdown_from_120d_high"] = d["close"] / d["close"].rolling(120).max() - 1
    d["volatility_20d"] = d["close"].pct_change().rolling(20).std()
    d["volume_ratio_5d"] = d["volume"] / d["volume"].rolling(5).mean()
    d["amount_ratio_5d"] = d["amount"] / d["amount"].rolling(5).mean()
    return d
