"""Mock data source for demo mode when external market APIs are unavailable."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from app.data_sources.base import BaseDataSource

MOCK_STOCKS = [
    ("300308", "中际旭创"), ("601138", "工业富联"), ("688256", "寒武纪"), ("688041", "海光信息"), ("688981", "中芯国际"),
    ("002371", "北方华创"), ("002463", "沪电股份"), ("002916", "深南电路"), ("002475", "立讯精密"), ("002241", "歌尔股份"),
    ("000977", "浪潮信息"), ("000938", "紫光股份"), ("603019", "中科曙光"), ("600845", "宝信软件"), ("600588", "用友网络"),
    ("002410", "广联达"), ("002230", "科大讯飞"), ("002236", "大华股份"), ("002415", "海康威视"), ("603986", "兆易创新"),
    ("603501", "韦尔股份"), ("688008", "澜起科技"), ("300782", "卓胜微"), ("600183", "生益科技"), ("603228", "景旺电子"),
    ("300476", "胜宏科技"), ("300024", "机器人"), ("002747", "埃斯顿"), ("300124", "汇川技术"), ("688777", "中控技术"),
]


class MockDataSource(BaseDataSource):
    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for i, (code, name) in enumerate(MOCK_STOCKS):
            base = 20 + i * 1.7
            drift = (i % 5 - 2) * 0.003
            pct = float(np.clip(drift + self.rng.normal(0, 0.015), -0.095, 0.095))
            price = round(base * (1 + pct), 2)
            change = round(price - base, 2)
            volume = float(2_000_000 + (i + 1) * 80_000 + abs(self.rng.normal(0, 300_000)))
            amount = float(volume * price)
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "price": price,
                    "pct_change": round(pct * 100, 2),
                    "change": change,
                    "volume": volume,
                    "amount": amount,
                    "turnover_rate": round(float(1.2 + (i % 10) * 0.45), 2),
                    "pe": round(float(20 + (i % 15) * 3.2), 2),
                    "pb": round(float(1.5 + (i % 8) * 0.5), 2),
                    "total_market_cap": float(80e9 + i * 15e9),
                    "float_market_cap": float(40e9 + i * 9e9),
                    "timestamp": ts,
                }
            )
        return pd.DataFrame(rows)

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # keep signature consistent with BaseDataSource and generate ~120 business days
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=120)
        idx = next((i for i, (c, _) in enumerate(MOCK_STOCKS) if c == code), 0)
        name = next((n for c, n in MOCK_STOCKS if c == code), code)
        base = 18 + idx * 1.6
        trend = np.linspace(0, 0.25, len(dates))
        cyc = 0.03 * np.sin(np.linspace(0, 8 * np.pi, len(dates)))
        noise = self.rng.normal(0, 0.008, len(dates))
        close = base * (1 + trend + cyc + noise)
        open_ = close * (1 + self.rng.normal(0, 0.004, len(dates)))
        high = np.maximum(open_, close) * (1 + np.abs(self.rng.normal(0.008, 0.004, len(dates))))
        low = np.minimum(open_, close) * (1 - np.abs(self.rng.normal(0.008, 0.004, len(dates))))
        volume = 1_800_000 + idx * 80_000 + np.abs(self.rng.normal(0, 220_000, len(dates)))
        amount = volume * close
        pct_change = np.insert(np.diff(close) / close[:-1], 0, 0.0) * 100
        turnover = 1.0 + (idx % 10) * 0.4 + np.abs(self.rng.normal(0, 0.15, len(dates)))
        return pd.DataFrame(
            {
                "code": code,
                "name": name,
                "trade_date": dates.strftime("%Y-%m-%d"),
                "open": open_.round(2),
                "high": high.round(2),
                "low": low.round(2),
                "close": close.round(2),
                "volume": volume,
                "amount": amount,
                "pct_change": pct_change.round(3),
                "turnover_rate": turnover.round(3),
            }
        )

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": c, "name": n} for c, n in MOCK_STOCKS if not symbols or c in symbols]
