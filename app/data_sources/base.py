"""Abstract data source interface."""
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseDataSource(ABC):
    @abstractmethod
    def get_realtime_quotes(self, symbols: list[str]) -> pd.DataFrame:
        ...

    @abstractmethod
    def fetch_daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch daily bars with normalized columns for one stock code."""

    @abstractmethod
    def get_basic_info(self, symbols: list[str]) -> list[dict[str, Any]]:
        ...
