"""Technology stock universe module backed by a curated CSV."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
UNIVERSE_CSV = BASE_DIR / "data" / "tech_universe_mainboard.csv"


def is_mainboard_code(code: str) -> bool:
    c = str(code)
    return c.startswith(("600", "601", "603", "605", "000", "001", "002"))


def to_sina_symbol(code: str) -> str:
    c = str(code)
    return f"sh{c}" if c.startswith(("600", "601", "603", "605")) else f"sz{c}"


def load_tech_universe_df() -> pd.DataFrame:
    df = pd.read_csv(UNIVERSE_CSV, dtype={"code": str})
    df = df[~df["name"].astype(str).str.contains(r"\*?ST", na=False)]
    df = df[df["code"].map(is_mainboard_code)]
    df = df.drop_duplicates(subset=["code"]).reset_index(drop=True)
    df["sina_symbol"] = df["code"].map(to_sina_symbol)
    return df


def get_tech_universe_codes() -> list[str]:
    return load_tech_universe_df()["code"].tolist()


def get_tech_universe_sina_symbols() -> list[str]:
    return load_tech_universe_df()["sina_symbol"].tolist()


def get_mock_tech_universe() -> list[dict[str, str]]:
    df = load_tech_universe_df().head(20)
    return df[["code", "name", "sector"]].to_dict(orient="records")
