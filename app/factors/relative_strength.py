import pandas as pd


def add_relative_strength_factors(df: pd.DataFrame, benchmark_returns: pd.Series | None = None) -> pd.DataFrame:
    d = df.sort_values("trade_date").copy()
    d["stock_return_5d"] = d["close"].pct_change(5)
    d["stock_return_20d"] = d["close"].pct_change(20)
    if benchmark_returns is None:
        # TODO: replace with HS300/tech index data source.
        benchmark_returns = pd.Series(0.0, index=d.index)
    d["benchmark_return_5d"] = benchmark_returns
    d["benchmark_return_20d"] = benchmark_returns
    d["excess_return_5d"] = d["stock_return_5d"] - d["benchmark_return_5d"]
    d["excess_return_20d"] = d["stock_return_20d"] - d["benchmark_return_20d"]
    d["relative_strength_score"] = ((d["excess_return_5d"].fillna(0) * 0.4 + d["excess_return_20d"].fillna(0) * 0.6) * 100).clip(-100, 100)
    return d
