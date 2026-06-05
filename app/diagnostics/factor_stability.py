from __future__ import annotations

import pandas as pd


def rolling_stability(series: pd.Series, window: int = 20) -> float:
    if len(series) < window:
        return 0.5
    roll_std = series.rolling(window).std().dropna()
    if roll_std.empty:
        return 0.5
    return float(max(0.0, min(1.0, 1.0 / (1.0 + float(roll_std.mean())))))
