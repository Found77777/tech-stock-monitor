from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BreadthMetrics:
    adv_decl_ratio: float
    pct_above_ma20: float
    pct_above_ma60: float
    new_high_low_ratio: float


def compute_breadth(snapshot_stats: dict) -> BreadthMetrics:
    adv = float(snapshot_stats.get("advancers", 0) or 0)
    dec = float(snapshot_stats.get("decliners", 0) or 0)
    adv_decl_ratio = adv / (dec + 1e-9)
    return BreadthMetrics(
        adv_decl_ratio=adv_decl_ratio,
        pct_above_ma20=float(snapshot_stats.get("pct_above_ma20", 0.5) or 0.5),
        pct_above_ma60=float(snapshot_stats.get("pct_above_ma60", 0.5) or 0.5),
        new_high_low_ratio=float(snapshot_stats.get("new_high_low_ratio", 1.0) or 1.0),
    )
