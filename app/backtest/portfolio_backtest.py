from __future__ import annotations

import pandas as pd

from app.backtest.metrics import annualized_return, annualized_volatility, cumulative_return, max_drawdown, sharpe_ratio, turnover, win_rate


def run_top_score_backtest(score_df: pd.DataFrame, bars_df: pd.DataFrame, top_n: int = 20, hold_days: int = 5, transaction_cost_bps: float = 0.0) -> dict:
    b = bars_df.sort_values(["trade_date", "code"]).copy()
    b["fwd_ret"] = b.groupby("code")["close"].shift(-hold_days) / b["close"] - 1
    merged = score_df.merge(b[["code", "trade_date", "fwd_ret"]], on=["code", "trade_date"], how="left")
    daily = []
    holds = []
    for td, x in merged.groupby("trade_date"):
        top = x.sort_values("total_score", ascending=False).head(top_n)
        holds.append(set(top["code"].tolist()))
        r = top["fwd_ret"].mean()
        if pd.isna(r):
            continue
        daily.append((td, float(r - transaction_cost_bps / 10000)))
    ret = pd.Series([x[1] for x in daily], index=[x[0] for x in daily]).sort_index()
    nav = (1 + ret).cumprod()
    return {
        "nav_curve": [{"trade_date": str(i), "nav": float(v)} for i, v in nav.items()],
        "metrics": {
            "cumulative_return": cumulative_return(nav),
            "annualized_return": annualized_return(nav),
            "annualized_volatility": annualized_volatility(ret),
            "sharpe_ratio": sharpe_ratio(ret),
            "max_drawdown": max_drawdown(nav),
            "win_rate": win_rate(ret),
            "turnover": turnover(holds),
        },
    }
