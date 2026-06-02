from __future__ import annotations


def event_excess_return(avg_benchmark_ret: float, event_ret: float) -> float:
    return float(event_ret - avg_benchmark_ret)
