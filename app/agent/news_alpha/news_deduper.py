from __future__ import annotations


def dedupe_news(items: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for x in items:
        key = (str(x.get("title", "")).strip(), str(x.get("url", "")).strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out
