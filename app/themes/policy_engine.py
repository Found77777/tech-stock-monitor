from __future__ import annotations

from app.themes.theme_registry import load_theme_registry


POLICY_MAP = {
    "national_core": 92,
    "strategic": 80,
    "support": 68,
    "related": 55,
}


def policy_alignment_score(primary_theme: str, fallback_theme: str | None = None) -> float:
    df = load_theme_registry()
    row = df[df["theme"] == primary_theme]
    if row.empty and fallback_theme:
        row = df[df["theme"] == fallback_theme]
    if row.empty:
        return 45.0
    level = str(row.iloc[0]["policy_level"])
    return float(POLICY_MAP.get(level, 55))
