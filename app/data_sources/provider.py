"""Unified market data provider selection and fallback."""
from __future__ import annotations

from app.config import get_settings
from app.data_sources.akshare_source import AKShareDataSource
from app.data_sources.base import BaseDataSource
from app.data_sources.efinance_source import EFinanceDataSource
from app.data_sources.mock_source import MockDataSource
from app.data_sources.pytdx_source import PytdxDataSource
from app.data_sources.sina_source import SinaDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)


def build_data_source(name: str) -> BaseDataSource:
    source = str(name or "").lower()
    if source == "efinance":
        return EFinanceDataSource()
    if source == "sina":
        return SinaDataSource()
    if source == "akshare":
        return AKShareDataSource()
    if source == "pytdx":
        return PytdxDataSource()
    if source == "mock":
        return MockDataSource()
    raise ValueError(f"unknown REAL_DATA_SOURCE={name}")


def fallback_chain(primary: str, enable_fallback: bool | None = None) -> list[str]:
    settings = get_settings()
    if settings.use_mock_data:
        return ["mock"]
    primary = str(primary or "efinance").lower()
    if enable_fallback is None:
        enable_fallback = bool(getattr(settings, "enable_data_source_fallback", True))
    if not enable_fallback:
        return [primary]
    chains = {
        "efinance": ["efinance", "sina", "mock"],
        "akshare": ["akshare", "efinance", "sina", "mock"],
        "sina": ["sina", "mock"],
        "mock": ["mock"],
        "pytdx": ["pytdx", "efinance", "sina", "mock"],
    }
    return chains.get(primary, [primary, "efinance", "sina", "mock"])


def primary_source_name() -> str:
    settings = get_settings()
    return "mock" if settings.use_mock_data else str(settings.real_data_source or "efinance").lower()
