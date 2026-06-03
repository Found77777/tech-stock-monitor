from __future__ import annotations


def turnover(prev_codes: set[str], new_codes: set[str]) -> float:
    if not prev_codes and not new_codes:
        return 0.0
    return float(len(prev_codes.symmetric_difference(new_codes)) / max(len(prev_codes.union(new_codes)), 1))
