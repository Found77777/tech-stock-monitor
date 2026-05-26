from __future__ import annotations

import numpy as np
import pandas as pd

SCORE_COLS = ["total_score", "trend_score", "momentum_score", "relative_strength_score", "liquidity_score", "position_score"]


def add_forward_returns(df: pd.DataFrame, benchmark_col: str | None = None) -> pd.DataFrame:
    """Compute forward returns by code using future close without look-ahead leakage."""
    d = df.sort_values(["code", "trade_date"]).copy()
    g = d.groupby("code", group_keys=False)
    d["forward_return_1d"] = g["close"].shift(-1) / d["close"] - 1
    d["forward_return_5d"] = g["close"].shift(-5) / d["close"] - 1
    d["forward_return_20d"] = g["close"].shift(-20) / d["close"] - 1
    if benchmark_col and benchmark_col in d.columns:
        d["excess_forward_return_5d"] = d["forward_return_5d"] - d[benchmark_col]
        d["excess_forward_return_20d"] = d["forward_return_20d"] - d[benchmark_col]
    else:
        d["excess_forward_return_5d"] = d["forward_return_5d"]
        d["excess_forward_return_20d"] = d["forward_return_20d"]
    return d


def daily_ic_series(df: pd.DataFrame, factor_col: str, ret_col: str, method: str = "spearman") -> pd.Series:
    vals = {}
    for td, x in df.groupby("trade_date"):
        x = x[[factor_col, ret_col]].dropna()
        if len(x) < 5:
            continue
        if method == "spearman":
            vals[td] = x[factor_col].rank().corr(x[ret_col].rank(), method="pearson")
        else:
            vals[td] = x[factor_col].corr(x[ret_col], method="pearson")
    return pd.Series(vals).sort_index()


def ic_summary(ic_s: pd.Series) -> dict:
    if ic_s.empty:
        return {"mean_ic": 0.0, "ic_std": 0.0, "ic_ir": 0.0, "ic_positive_ratio": 0.0, "sample_days": 0}
    std = float(ic_s.std(ddof=0))
    mean = float(ic_s.mean())
    return {
        "mean_ic": mean,
        "ic_std": std,
        "ic_ir": 0.0 if std == 0 else mean / std,
        "ic_positive_ratio": float((ic_s > 0).mean()),
        "sample_days": int(ic_s.shape[0]),
    }


def factor_group_test(df: pd.DataFrame, factor_col: str, ret_col: str, groups: int = 5) -> dict:
    rows = []
    for td, x in df.groupby("trade_date"):
        x = x[[factor_col, ret_col]].dropna()
        if len(x) < groups:
            continue
        x = x.copy()
        x["grp"] = pd.qcut(x[factor_col].rank(method="first"), groups, labels=False) + 1
        m = x.groupby("grp")[ret_col].mean().to_dict()
        rows.append(m)
    if not rows:
        return {"group_returns": {}, "top_bottom_spread": 0.0, "monotonic": False}
    gm = pd.DataFrame(rows).mean().to_dict()
    spread = gm.get(groups, 0.0) - gm.get(1, 0.0)
    arr = [gm.get(i, np.nan) for i in range(1, groups + 1)]
    mono = all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1) if not (pd.isna(arr[i]) or pd.isna(arr[i + 1])))
    return {"group_returns": {str(k): float(v) for k, v in gm.items()}, "top_bottom_spread": float(spread), "monotonic": bool(mono)}
