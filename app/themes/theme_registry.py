from __future__ import annotations

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
REGISTRY_CSV = BASE_DIR / "data" / "theme_registry.csv"


def load_theme_registry() -> pd.DataFrame:
    df = pd.read_csv(REGISTRY_CSV)
    for c in ["theme", "policy_level", "core_keywords", "core_sectors", "related_sectors", "priority"]:
        if c not in df.columns:
            df[c] = ""
    return df
