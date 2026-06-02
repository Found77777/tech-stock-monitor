from __future__ import annotations

import pandas as pd


def decay_curve(signal: pd.Series, returns_by_horizon: dict[int, pd.Series]) -> dict[int, float]:
    out = {}
    for h, r in returns_by_horizon.items():
        x = pd.concat([signal, r], axis=1).dropna()
        out[h] = float(x.iloc[:, 0].corr(x.iloc[:, 1]) or 0.0) if not x.empty else 0.0
    return out
