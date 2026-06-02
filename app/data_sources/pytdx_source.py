"""pytdx real-time quote source for A-share."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
from pytdx.hq import TdxHq_API

from app.data_sources.base import BaseDataSource


class PytdxDataSource(BaseDataSource):
    # Commonly available quote servers; fallback iteration.
    SERVERS = [
        ("119.147.212.81", 7709),
        ("114.80.149.22", 7709),
        ("180.153.18.170", 7709),
    ]

    def _connect(self):
        api = TdxHq_API()
        for host, port in self.SERVERS:
            if api.connect(host, port, time_out=1):
                return api
        raise ConnectionError("pytdx connect failed for all configured servers")

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        if not symbols:
            symbols = [
                "300308", "601138", "688256", "688041", "688981", "002371", "002463", "002916", "002475", "002241",
                "000977", "000938", "603019", "600845", "600588", "002410", "002230", "002236", "002415", "603986",
                "603501", "688008", "300782", "600183", "603228", "300476", "300024", "002747", "300124", "688777",
            ]
        pairs = []
        for c in symbols:
            market = 1 if str(c).startswith("6") else 0  # sh=1, sz=0
            pairs.append((market, str(c)))

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        api = self._connect()
        try:
            for i in range(0, len(pairs), 80):
                batch = pairs[i:i + 80]
                data = api.get_security_quotes(batch) or []
                for q in data:
                    price = float(q.get("price", 0) or 0)
                    last_close = float(q.get("last_close", 0) or 0)
                    change = (price - last_close) if last_close else 0.0
                    pct = (change / last_close * 100) if last_close else 0.0
                    rows.append(
                        {
                            "code": str(q.get("code", "")),
                            "name": str(q.get("name", "")),
                            "price": price,
                            "pct_change": pct,
                            "change": change,
                            "volume": float(q.get("vol", 0) or 0),
                            "amount": float(q.get("amount", 0) or 0),
                            "turnover_rate": None,
                            "pe": None,
                            "pb": None,
                            "total_market_cap": None,
                            "float_market_cap": None,
                            "timestamp": now,
                        }
                    )
        finally:
            api.disconnect()
        return pd.DataFrame(rows)

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"])

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": s, "name": s} for s in symbols]
