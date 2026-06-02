"""EFinance historical capital-flow provider.

This module intentionally clears system proxy environment variables only around
``ef.stock.get_history_bill`` because EastMoney/efinance endpoints can fail when
process-wide HTTP(S) proxies are inherited from the shell. LLM proxy settings are
stored in application config and are not read from these environment variables.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterable

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

PROXY_ENV_VARS = ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy")
MAIN_NET_INFLOW_COLUMNS = (
    "主力净流入",
    "主力净流入净额",
    "主力净流入-净额",
    "主力净额",
    "主力资金净流入",
)
DATE_COLUMNS = ("日期", "时间", "date", "trade_date")


def norm_code(code: str) -> str:
    digits = "".join(ch for ch in str(code or "") if ch.isdigit())
    return digits[-6:].zfill(6) if digits else ""


@contextmanager
def without_system_proxies():
    """Temporarily clear process proxy env vars and restore them afterwards."""
    saved = {key: os.environ.get(key) for key in PROXY_ENV_VARS}
    try:
        for key in PROXY_ENV_VARS:
            os.environ[key] = ""
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _pick_column(columns: Iterable[str], candidates: Iterable[str], contains: str | None = None) -> str | None:
    cols = [str(c) for c in columns]
    for candidate in candidates:
        if candidate in cols:
            return candidate
    if contains:
        for col in cols:
            if contains in col and "占比" not in col and "比例" not in col:
                return col
    return None


def parse_money(value) -> float:
    """Parse efinance Chinese money strings to yuan-like numeric values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "-", "nan", "None"}:
        return 0.0
    multiplier = 1.0
    if text.endswith("亿"):
        multiplier = 100_000_000.0
        text = text[:-1]
    elif text.endswith("万"):
        multiplier = 10_000.0
        text = text[:-1]
    elif text.endswith("元"):
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
        return float(cleaned) * multiplier if cleaned else 0.0


def normalize_history_bill(raw_df: pd.DataFrame, code: str) -> dict:
    """Normalize efinance get_history_bill output into project metrics."""
    norm = norm_code(code)
    if raw_df is None or raw_df.empty:
        raise ValueError("empty efinance history bill")
    df = raw_df.copy()
    main_col = _pick_column(df.columns, MAIN_NET_INFLOW_COLUMNS, contains="主力净流入")
    if not main_col:
        logger.warning("efinance history bill missing main inflow column code=%s columns=%s", norm, list(df.columns))
        raise KeyError("missing main capital inflow column")
    date_col = _pick_column(df.columns, DATE_COLUMNS)
    df["_main_net_inflow"] = df[main_col].map(parse_money)
    if date_col:
        df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
        if df["_date"].notna().any():
            df = df.sort_values("_date")
    tail10 = df.tail(10).copy()
    tail5 = tail10.tail(5)
    recent = tail10.iloc[-1]
    values_desc = list(reversed(tail10["_main_net_inflow"].tolist()))
    consecutive = 0
    for value in values_desc:
        if value > 0:
            consecutive += 1
        else:
            break
    n5 = float(tail5["_main_net_inflow"].sum())
    n10 = float(tail10["_main_net_inflow"].sum())
    p5 = int((tail5["_main_net_inflow"] > 0).sum())
    p10 = int((tail10["_main_net_inflow"] > 0).sum())
    return {
        "stock_code": norm,
        "net_inflow_1d": float(recent["_main_net_inflow"]),
        "net_inflow_5d": n5,
        "net_inflow_10d": n10,
        "consecutive_net_inflow_days": int(consecutive),
        "net_inflow_days_5d": p5,
        "net_inflow_days_10d": p10,
        "history_bill_rows": int(len(df)),
    }


def fetch_efinance_history_bill(code: str) -> dict:
    """Fetch and normalize one stock's efinance history bill data."""
    norm = norm_code(code)
    with without_system_proxies():
        import efinance as ef
        raw = ef.stock.get_history_bill(norm)
    return normalize_history_bill(raw, norm)
