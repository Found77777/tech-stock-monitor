from __future__ import annotations

import pandas as pd


def information_coefficient(factor: pd.Series, fwd_ret: pd.Series) -> float:
    x = pd.concat([factor, fwd_ret], axis=1).dropna()
    if x.empty:
        return 0.0
    return float(x.iloc[:, 0].corr(x.iloc[:, 1], method="spearman") or 0.0)
