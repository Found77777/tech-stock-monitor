from __future__ import annotations


def effective_factor_count(clusters: list[list[str]]) -> int:
    return max(1, len(clusters))
