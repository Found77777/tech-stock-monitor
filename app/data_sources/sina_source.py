"""Sina real-time quote source (non-EastMoney)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import requests

from app.config import get_settings
from app.data_sources.base import BaseDataSource


class SinaDataSource(BaseDataSource):
    BASE_URL = "https://hq.sinajs.cn/list="

    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _to_sina_symbol(code: str) -> str:
        code = str(code)
        return ("sh" + code) if code.startswith("6") else ("sz" + code)

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        # If symbols empty, use a broad A-share tech candidate basket.
        if not symbols:
            symbols = [
                "300308", "601138", "688256", "688041", "688981", "002371", "002463", "002916", "002475", "002241",
                "000977", "000938", "603019", "600845", "600588", "002410", "002230", "002236", "002415", "603986",
                "603501", "688008", "300782", "600183", "603228", "300476", "300024", "002747", "300124", "688777",
            ]
        sina_symbols = [self._to_sina_symbol(s) for s in symbols]
        headers = {"Referer": "https://finance.sina.com.cn"}
        if self.settings.sina_user_agent:
            headers["User-Agent"] = self.settings.sina_user_agent
        if self.settings.sina_cookie:
            headers["Cookie"] = self.settings.sina_cookie
        resp = requests.get(self.BASE_URL + ",".join(sina_symbols), headers=headers, timeout=15)
        resp.raise_for_status()
        resp.encoding = "gbk"
        return self.normalize_sina_text(resp.text)

    def normalize_sina_text(self, text: str) -> pd.DataFrame:
        rows = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for line in text.strip().splitlines():
            if "=" not in line:
                continue
            left, right = line.split("=", 1)
            raw_symbol = left.replace("var hq_str_", "").strip()
            code = raw_symbol[-6:]
            payload = right.strip().strip(';').strip('"')
            parts = payload.split(",")
            if len(parts) < 10 or not parts[0]:
                continue
            name = parts[0]
            try:
                prev_close = float(parts[2]) if parts[2] else 0.0
                price = float(parts[3]) if parts[3] else 0.0
                volume = float(parts[8]) if parts[8] else 0.0
                amount = float(parts[9]) if parts[9] else 0.0
            except ValueError:
                prev_close, price, volume, amount = 0.0, 0.0, 0.0, 0.0
            change = (price - prev_close) if prev_close else 0.0
            pct_change = (change / prev_close * 100) if prev_close else 0.0
            rows.append(
                {
                    "code": code,
                    "name": name,
                    "price": round(price, 3) if price else 0.0,
                    "pct_change": round(pct_change, 3) if prev_close else 0.0,
                    "change": round(change, 3) if prev_close else 0.0,
                    "volume": volume,
                    "amount": amount,
                    "turnover_rate": None,
                    "pe": None,
                    "pb": None,
                    "total_market_cap": None,
                    "float_market_cap": None,
                    "timestamp": now,
                }
            )
        return pd.DataFrame(rows)

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        # TODO: Sina daily kline endpoint integration can be added later.
        return pd.DataFrame(columns=["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"])

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": s, "name": s} for s in symbols]
