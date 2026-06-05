from __future__ import annotations

from app.themes.theme_registry import load_theme_registry


def _tokens(s: str) -> list[str]:
    return [x.strip() for x in str(s or "").split("|") if x.strip()]


def classify_theme(row: dict) -> dict:
    text = " ".join([
        str(row.get("sector", "")),
        str(row.get("theme", "")),
        str(row.get("policy_theme", "")),
        str(row.get("name", "")),
    ]).lower()
    registry = load_theme_registry().sort_values("priority", ascending=False)

    matches: list[tuple[str, float]] = []
    for _, r in registry.iterrows():
        score = 0.0
        for kw in _tokens(r["core_keywords"]):
            if kw.lower() in text:
                score += 1.0
        for kw in _tokens(r["core_sectors"]):
            if kw.lower() in text:
                score += 1.2
        for kw in _tokens(r["related_sectors"]):
            if kw.lower() in text:
                score += 0.6
        if score > 0:
            matches.append((str(r["theme"]), score))

    if not matches:
        fallback = str(row.get("policy_theme") or row.get("theme") or "国产替代")
        return {"primary_theme": fallback, "secondary_theme": "", "theme_strength": 35.0}

    matches.sort(key=lambda x: x[1], reverse=True)
    primary = matches[0][0]
    secondary = matches[1][0] if len(matches) > 1 else ""
    strength = min(100.0, 40.0 + matches[0][1] * 15.0)
    return {"primary_theme": primary, "secondary_theme": secondary, "theme_strength": strength}
