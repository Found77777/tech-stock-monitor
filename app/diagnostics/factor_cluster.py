from __future__ import annotations


def cluster_from_correlation(corr: dict[str, dict], threshold: float = 0.8) -> list[list[str]]:
    cols = list(corr.keys())
    seen = set()
    groups = []
    for c in cols:
        if c in seen:
            continue
        g = [c]
        seen.add(c)
        for d, v in corr.get(c, {}).items():
            if d not in seen and abs(float(v)) >= threshold:
                g.append(d)
                seen.add(d)
        groups.append(g)
    return groups
