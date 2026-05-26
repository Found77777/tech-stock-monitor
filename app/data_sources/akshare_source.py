"""AKShare data source implementation."""
from __future__ import annotations

import akshare as ak
import pandas as pd

from app.data_sources.base import BaseDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AKShareDataSource(BaseDataSource):
    CN_TO_EN = {
        "代码": "code",
        "名称": "name",
        "最新价": "price",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "成交量": "volume",
        "成交额": "amount",
        "换手率": "turnover_rate",
        "市盈率-动态": "pe",
        "市净率": "pb",
        "总市值": "total_market_cap",
        "流通市值": "float_market_cap",
    }

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        raw = ak.stock_zh_a_spot_em()
        return self.normalize_spot_df(raw)

    def normalize_spot_df(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        df = raw_df.rename(columns=self.CN_TO_EN)
        for col in self.CN_TO_EN.values():
            if col not in df.columns:
                df[col] = 0
        cols = list(self.CN_TO_EN.values())
        df = df[cols].copy()
        for col in ["price", "pct_change", "change", "volume", "amount", "turnover_rate", "pe", "pb", "total_market_cap", "float_market_cap"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        df["code"] = df["code"].astype(str)
        df["name"] = df["name"].astype(str)
        return df

    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily history via AKShare and normalize.

        TODO: some fields may be unavailable depending on source endpoint.
        """
        try:
            logger.info("fetch_daily_bars start code=%s start=%s end=%s", code, start_date, end_date)
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''), adjust="")
            if df is None or df.empty:
                return pd.DataFrame(columns=["code","name","trade_date","open","high","low","close","volume","amount","pct_change","turnover_rate"])
            rename_map = {"日期":"trade_date","开盘":"open","收盘":"close","最高":"high","最低":"low","成交量":"volume","成交额":"amount","涨跌幅":"pct_change","换手率":"turnover_rate"}
            df = df.rename(columns=rename_map)
            for col in ["trade_date","open","high","low","close","volume","amount","pct_change","turnover_rate"]:
                if col not in df.columns:
                    df[col] = None  # TODO: fill from other endpoints
            out = df[["trade_date","open","high","low","close","volume","amount","pct_change","turnover_rate"]].copy()
            out["code"] = code
            out["name"] = code  # TODO: resolve name from basic info cache
            cols = ["code","name","trade_date","open","high","low","close","volume","amount","pct_change","turnover_rate"]
            out = out[cols]
            for c in ["open","high","low","close","volume","amount","pct_change","turnover_rate"]:
                out[c] = pd.to_numeric(out[c], errors="coerce")
            return out
        except Exception as e:
            logger.exception("fetch_daily_bars failed code=%s err=%s", code, e)
            return pd.DataFrame(columns=["code","name","trade_date","open","high","low","close","volume","amount","pct_change","turnover_rate"])

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        return [{"symbol": s, "name": f"{s}"} for s in symbols]
