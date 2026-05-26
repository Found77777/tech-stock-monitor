from __future__ import annotations

import numpy as np
import pandas as pd


def cumulative_return(nav: pd.Series) -> float: return float(nav.iloc[-1] / nav.iloc[0] - 1) if len(nav) else 0.0

def annualized_return(nav: pd.Series, periods_per_year: int = 252) -> float:
    if len(nav) < 2: return 0.0
    return float((nav.iloc[-1] / nav.iloc[0]) ** (periods_per_year / (len(nav)-1)) - 1)

def annualized_volatility(ret: pd.Series, periods_per_year: int = 252) -> float: return float(ret.std(ddof=0) * np.sqrt(periods_per_year)) if len(ret) else 0.0

def sharpe_ratio(ret: pd.Series) -> float:
    vol = annualized_volatility(ret)
    return 0.0 if vol == 0 else float(ret.mean() * 252 / vol)

def max_drawdown(nav: pd.Series) -> float:
    if len(nav) == 0: return 0.0
    dd = nav / nav.cummax() - 1
    return float(dd.min())

def win_rate(ret: pd.Series) -> float: return float((ret > 0).mean()) if len(ret) else 0.0

def turnover(holdings: list[set[str]]) -> float:
    if len(holdings) < 2: return 0.0
    vals = []
    for i in range(1, len(holdings)):
        prev, cur = holdings[i-1], holdings[i]
        vals.append(1 - (len(prev & cur) / max(1, len(prev | cur))))
    return float(np.mean(vals)) if vals else 0.0
