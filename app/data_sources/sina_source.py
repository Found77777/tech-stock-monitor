"""Sina quote and advanced daily K-line source (non-EastMoney)."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import requests

from app.config import get_settings
from app.data_sources.base import BaseDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SinaDataSource(BaseDataSource):
    BASE_URL = "https://hq.sinajs.cn/list="
    KLINE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
    HISTORY_COLUMNS = [
        "code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount",
        "pct_change", "turnover_rate", "amount_estimated", "turnover_rate_estimated", "volume_raw",
    ]

    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _norm_code(code: str) -> str:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        return digits[-6:].zfill(6) if digits else ""

    @staticmethod
    def _to_sina_symbol(code: str) -> str:
        norm = SinaDataSource._norm_code(code)
        if str(code).startswith(("sh", "sz")) and len(str(code)) >= 8:
            return str(code)[:2] + norm
        return ("sh" + norm) if norm.startswith("6") else ("sz" + norm)

    def _build_headers(self) -> dict[str, str]:
        headers = {"Referer": "https://finance.sina.com.cn/", "Accept": "*/*", "Connection": "keep-alive"}
        headers["User-Agent"] = self.settings.sina_user_agent or "Mozilla/5.0"
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
        if v is None or isinstance(v, (dict, list, tuple)):
            return None
        try:
            return float(v)
        except Exception:
            return None

    @staticmethod
    def _empty_history() -> pd.DataFrame:
        return pd.DataFrame(columns=SinaDataSource.HISTORY_COLUMNS)

    @staticmethod
    def _parse_kline_payload(text: str) -> list[dict[str, Any]]:
        text = (text or "").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except Exception:
            pass
        # Defensive fallback for Sina variants that emit unquoted JS object keys.
        normalized = re.sub(r"([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', text)
        try:
            data = json.loads(normalized)
            return data if isinstance(data, list) else []
        except Exception:
            logger.warning("sina advanced kline parse failed sample=%s", text[:120])
            return []

    def get_history(
        self,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        days: int = 400,
        float_shares: float | None = None,
    ) -> pd.DataFrame:
        norm = self._norm_code(code)
        if not norm:
            return self._empty_history()
        end_dt = pd.to_datetime(end_date).date() if end_date else date.today()
        lookback_days = max(int(days or 400), 1)
        start_dt = pd.to_datetime(start_date).date() if start_date else end_dt - timedelta(days=lookback_days * 2)
        symbol = self._to_sina_symbol(norm)
        resp = requests.get(
            self.KLINE_URL,
            params={"symbol": symbol, "scale": 240, "ma": "no", "datalen": lookback_days},
            headers=self._build_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return self.normalize_history_payload(resp.text, norm, start_dt.isoformat(), end_dt.isoformat(), float_shares=float_shares)

    def normalize_history_payload(
        self,
        text: str,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        float_shares: float | None = None,
    ) -> pd.DataFrame:
        rows = self._parse_kline_payload(text)
        return self.normalize_history_rows(rows, code=code, start_date=start_date, end_date=end_date, float_shares=float_shares)

    def normalize_history_rows(
        self,
        rows: list[dict[str, Any]],
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        float_shares: float | None = None,
    ) -> pd.DataFrame:
        norm = self._norm_code(code)
        start = str(start_date) if start_date else None
        end = str(end_date) if end_date else None
        out: list[dict[str, Any]] = []
        prev_close: float | None = None
        for item in rows or []:
            if not isinstance(item, dict):
                continue
            trade_date = str(item.get("day") or item.get("trade_date") or "")[:10]
            if not trade_date or (start and trade_date < start) or (end and trade_date > end):
                continue
            o = self._to_float(item.get("open"))
            h = self._to_float(item.get("high"))
            l = self._to_float(item.get("low"))
            c = self._to_float(item.get("close"))
            volume_raw = self._to_float(item.get("volume"))
            if None in (o, h, l, c, volume_raw):
                continue
            # Project daily_bars.volume is kept in hands for compatibility with existing volume-ratio factors.
            # Sina advanced K-line volume_raw is treated as shares for amount estimation.
            volume_shares = float(volume_raw or 0.0)
            volume_hands = volume_shares / 100.0
            avg_price = (float(o) + float(h) + float(l) + float(c)) / 4.0
            amount = avg_price * volume_shares if volume_shares > 0 and avg_price > 0 else None
            pct_change = ((float(c) - prev_close) / prev_close * 100) if (prev_close not in (None, 0) and c is not None) else None
            turnover_rate = None
            if float_shares:
                try:
                    fs = float(float_shares)
                    if fs > 0:
                        turnover_rate = volume_shares / fs * 100
                except Exception:
                    turnover_rate = None
            out.append({
                "code": norm,
                "name": None,
                "trade_date": trade_date,
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
                "volume": volume_hands,
                "amount": amount,
                "pct_change": pct_change,
                "turnover_rate": turnover_rate,
                "amount_estimated": amount is not None,
                "turnover_rate_estimated": False,
                "volume_raw": volume_raw,
            })
            prev_close = float(c)
        if not out:
            logger.warning("sina advanced kline empty code=%s", norm)
            return self._empty_history()
        return pd.DataFrame(out, columns=self.HISTORY_COLUMNS)

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            days = max((pd.to_datetime(end_date).date() - pd.to_datetime(start_date).date()).days + 1, 1)
        except Exception:
            days = 400
        try:
            return self.get_history(code=code, start_date=start_date, end_date=end_date, days=days)
        except Exception as exc:
            logger.warning("sina advanced kline failed code=%s err=%s", self._norm_code(code), exc)
            return self._empty_history()

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": s, "name": s} for s in symbols]
