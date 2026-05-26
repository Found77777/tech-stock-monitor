"""Tushare data source skeleton."""
import pandas as pd

from app.data_sources.base import BaseDataSource


class TushareDataSource(BaseDataSource):
    """Tushare implementation placeholder."""

    def __init__(self, token: str) -> None:
        self.token = token

    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        """TODO: Integrate tushare real-time API."""
        return pd.DataFrame({"symbol": symbols, "price": [11.0] * len(symbols)})

    def get_daily_bars(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """TODO: Integrate tushare daily bars API."""
        return pd.DataFrame(
            [{"symbol": symbol, "date": start_date, "open": 11.0, "high": 11.5, "low": 10.8, "close": 11.2, "volume": 120000}]
        )

    def get_basic_info(self, symbols: list[str]) -> list[dict[str, str]]:
        """TODO: Integrate tushare stock basic API."""
        return [{"symbol": s, "name": f"Mock-{s}"} for s in symbols]
