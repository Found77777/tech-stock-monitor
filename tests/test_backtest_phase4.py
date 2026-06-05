import pandas as pd

from app.backtest.factor_test import add_forward_returns, daily_ic_series, factor_group_test
from app.backtest.metrics import max_drawdown
from app.backtest.portfolio_backtest import run_top_score_backtest


def test_forward_return_no_lookahead_shape():
    df = pd.DataFrame({"code":["A"]*6,"trade_date":[f"2026-01-0{i}" for i in range(1,7)],"close":[10,11,12,13,14,15]})
    out = add_forward_returns(df)
    assert round(out.iloc[0]["forward_return_1d"],4) == 0.1
    assert pd.isna(out.iloc[-1]["forward_return_1d"])


def test_ic_calc():
    df = pd.DataFrame({"trade_date":["d1"]*6+["d2"]*6,"factor":[1,2,3,4,5,6,1,2,3,4,5,6],"ret":[1,2,3,4,5,6,6,5,4,3,2,1]})
    ic = daily_ic_series(df.rename(columns={"factor":"total_score","ret":"forward_return_5d"}), "total_score", "forward_return_5d")
    assert len(ic) == 2


def test_group_logic():
    df = pd.DataFrame({"trade_date":["d1"]*10,"total_score":list(range(10)),"forward_return_5d":[x/100 for x in range(10)]})
    r = factor_group_test(df, "total_score", "forward_return_5d", groups=5)
    assert "top_bottom_spread" in r


def test_max_drawdown():
    nav = pd.Series([1,1.2,1.1,0.9,0.95])
    assert round(max_drawdown(nav),2) == -0.25


def test_topn_backtest_nav_curve():
    scores = pd.DataFrame({"code":["A","B","A","B"],"trade_date":["2026-01-01","2026-01-01","2026-01-02","2026-01-02"],"total_score":[90,80,88,85]})
    bars = pd.DataFrame({"code":["A","B","A","B","A","B","A","B"],"trade_date":["2026-01-01","2026-01-01","2026-01-02","2026-01-02","2026-01-03","2026-01-03","2026-01-04","2026-01-04"],"close":[10,10,11,10,12,10,13,10]})
    r = run_top_score_backtest(scores, bars, top_n=1, hold_days=1)
    assert len(r["nav_curve"]) >= 1
