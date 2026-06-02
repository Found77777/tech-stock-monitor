import sys
from types import SimpleNamespace

import pandas as pd

from app.data_sources.efinance_source import EFinanceDataSource


def test_efinance_realtime_normalizes_mainboard_fields():
    raw = pd.DataFrame([
        {"股票代码": "600850", "股票名称": "电科数字", "最新价": "10.5", "涨跌幅": "1.2", "成交量": "1000", "成交额": "90000000", "换手率": "2.3"},
        {"股票代码": "300001", "股票名称": "创业板", "最新价": "9", "涨跌幅": "1", "成交量": "1", "成交额": "1", "换手率": "1"},
        {"股票代码": "600001", "股票名称": "ST测试", "最新价": "9", "涨跌幅": "1", "成交量": "1", "成交额": "1", "换手率": "1"},
    ])
    df = EFinanceDataSource().normalize_spot_df(raw)
    assert list(df["code"]) == ["600850"]
    row = df.iloc[0]
    assert row["price"] == 10.5
    assert row["pct_change"] == 1.2
    assert row["amount"] == 90000000


def test_efinance_history_normalizes_fields():
    raw = pd.DataFrame([{"日期": "2026-05-20", "开盘": "10", "最高": "11", "最低": "9", "收盘": "10.5", "成交量": "1000", "成交额": "10000"}])
    df = EFinanceDataSource().normalize_history_df(raw, "600850")
    assert df.iloc[0]["code"] == "600850"
    assert df.iloc[0]["trade_date"] == "2026-05-20"
    assert df.iloc[0]["close"] == 10.5


def test_efinance_single_history_failure_returns_empty(monkeypatch):
    class Stock:
        @staticmethod
        def get_quote_history(*args, **kwargs):
            raise RuntimeError("one code failed")
    monkeypatch.setitem(sys.modules, "efinance", SimpleNamespace(stock=Stock()))
    df = EFinanceDataSource().fetch_daily_bars("600850", "2026-01-01", "2026-02-01")
    assert df.empty
