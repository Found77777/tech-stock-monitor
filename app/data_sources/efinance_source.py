"""EFinance market data source implementation."""
from __future__ import annotations

import pandas as pd

from app.data_sources.base import BaseDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _norm_code(code: str) -> str:
    digits = "".join(ch for ch in str(code or "") if ch.isdigit())
    return digits[-6:].zfill(6) if digits else ""


class EFinanceDataSource(BaseDataSource):
    """Real A-share quotes and daily bars via efinance."""

    SPOT_RENAME = {
        "股票代码": "code",
        "代码": "code",
        "股票名称": "name",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "成交量": "volume",
        "成交额": "amount",
        "换手率": "turnover_rate",
        "市盈率": "pe",
        "市净率": "pb",
        "总市值": "total_market_cap",
        "流通市值": "float_market_cap",
    }
    HISTORY_RENAME = {
        "日期": "trade_date",
        "开盘": "open",
        "收盘": "close",
        "最高": "high",
        "最低": "low",
        "成交量": "volume",
        "成交额": "amount",
        "涨跌幅": "pct_change",
        "换手率": "turnover_rate",
        "股票名称": "name",
        "名称": "name",
        "股票代码": "code",
        "代码": "code",
    }

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        import efinance as ef

        raw = ef.stock.get_realtime_quotes()
        return self.normalize_spot_df(raw, symbols=symbols)

    def normalize_spot_df(self, raw_df: pd.DataFrame, symbols: list[str] | None = None) -> pd.DataFrame:
        if raw_df is None or raw_df.empty:
            return pd.DataFrame(columns=["code", "name", "price", "pct_change", "change", "volume", "amount", "turnover_rate", "pe", "pb", "total_market_cap", "float_market_cap"])
        df = raw_df.rename(columns=self.SPOT_RENAME).copy()
        for col in ["code", "name", "price", "pct_change", "change", "volume", "amount", "turnover_rate", "pe", "pb", "total_market_cap", "float_market_cap"]:
            if col not in df.columns:
                df[col] = 0 if col not in {"code", "name"} else ""
        df["code"] = df["code"].map(_norm_code)
        df["name"] = df["name"].astype(str)
        if symbols:
            wanted = {_norm_code(s) for s in symbols}
            df = df[df["code"].isin(wanted)]
        df = df[~df["name"].str.contains(r"\*?ST", na=False)]
        df = df[df["code"].str.startswith(("600", "601", "603", "605", "000", "001", "002"))]
        for col in ["price", "pct_change", "change", "volume", "amount", "turnover_rate", "pe", "pb", "total_market_cap", "float_market_cap"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df[["code", "name", "price", "pct_change", "change", "volume", "amount", "turnover_rate", "pe", "pb", "total_market_cap", "float_market_cap"]].copy()

    def get_history(self, code: str, beg: str, end: str) -> pd.DataFrame:
        """Fetch quote history using efinance get_quote_history and normalize fields."""
        import efinance as ef

        norm = _norm_code(code)
        raw = ef.stock.get_quote_history(norm, beg=beg.replace("-", ""), end=end.replace("-", ""))
        return self.normalize_history_df(raw, norm)

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        norm = _norm_code(code)
        try:
            return self.get_history(norm, beg=start_date, end=end_date)
        except Exception as exc:
            logger.warning("efinance history failed code=%s err=%s", norm, exc)
            return pd.DataFrame(columns=["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"])

    def normalize_history_df(self, raw_df: pd.DataFrame, code: str) -> pd.DataFrame:
        norm = _norm_code(code)
        if raw_df is None or raw_df.empty:
            logger.warning("efinance history empty code=%s", norm)
            return pd.DataFrame(columns=["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"])
        df = raw_df.rename(columns=self.HISTORY_RENAME).copy()
        for col in ["trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate", "name"]:
            if col not in df.columns:
                df[col] = None
        df["code"] = norm
        df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.strftime("%Y-%m-%d")
        for col in ["open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        out = df[["code", "name", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_change", "turnover_rate"]].dropna(subset=["trade_date"])
        return out.copy()

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": _norm_code(s), "name": _norm_code(s)} for s in symbols]
