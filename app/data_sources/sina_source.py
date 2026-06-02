"""Sina/Tencent-compatible quote source (non-EastMoney)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

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
        if code.startswith(("sh", "sz")):
            return code
        return ("sh" + code) if code.startswith("6") else ("sz" + code)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Referer": "https://finance.sina.com.cn", "Accept": "*/*", "Connection": "keep-alive"}
        if self.settings.sina_user_agent:
            headers["User-Agent"] = self.settings.sina_user_agent
        if self.settings.sina_cookie:
            headers["Cookie"] = self.settings.sina_cookie
        return headers

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        if not symbols:
            return pd.DataFrame(columns=["code","name","price","pct_change","change","volume","amount","turnover_rate","pe","pb","total_market_cap","float_market_cap","timestamp"])
        sina_symbols = [self._to_sina_symbol(s) for s in symbols]
        parts = []
        headers = self._build_headers()
        for i in range(0, len(sina_symbols), 50):
            resp = requests.get(self.BASE_URL + ",".join(sina_symbols[i:i+50]), headers=headers, timeout=15)
            resp.raise_for_status()
            resp.encoding = "gbk"
            parts.append(self.normalize_sina_text(resp.text))
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

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
            rows.append({"code": code,"name": name,"price": round(price, 3) if price else 0.0,"pct_change": round(pct_change, 3) if prev_close else 0.0,"change": round(change, 3) if prev_close else 0.0,"volume": volume,"amount": amount,"turnover_rate": None,"pe": None,"pb": None,"total_market_cap": None,"float_market_cap": None,"timestamp": now})
        return pd.DataFrame(rows)

    @staticmethod
    def _to_float(v: Any) -> float | None:
        if v is None:
            return None
        if isinstance(v, (dict, list, tuple)):
            return None
        try:
            return float(v)
        except Exception:
            return None

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily bars from Tencent-compatible kline API (non-EastMoney)."""
        symbol = self._to_sina_symbol(code)
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},day,,,260,qfq"
        resp = requests.get(url, headers=self._build_headers(), timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        node = payload.get("data", {}).get(symbol, {})

        # only expand actual kline arrays; ignore metadata dicts
        day = node.get("qfqday") or node.get("day") or node.get("hfqday") or []
        if not isinstance(day, list) or not day:
            return pd.DataFrame(columns=["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"])

        rows = []
        prev_close = None
        for item in day:
            if not isinstance(item, (list, tuple)) or len(item) < 6:
                continue
            d = str(item[0])
            if d < start_date or d > end_date:
                continue
            o = self._to_float(item[1])
            c = self._to_float(item[2])
            h = self._to_float(item[3])
            l = self._to_float(item[4])
            v = self._to_float(item[5])
            amt = self._to_float(item[6]) if len(item) > 6 else None
            pct_change = ((c - prev_close) / prev_close * 100) if (prev_close not in (None, 0) and c is not None) else None
            rows.append({"code": str(code), "name": None, "trade_date": d, "open": o, "high": h, "low": l, "close": c, "volume": v, "amount": amt, "pct_change": pct_change, "turnover_rate": None})
            prev_close = c
        return pd.DataFrame(rows)

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": s, "name": s} for s in symbols]
