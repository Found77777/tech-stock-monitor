from __future__ import annotations


def calibrate_confidence(source_reliability: float, freshness: float, coverage: float, agreement: float) -> float:
    c = 0.35 * source_reliability + 0.25 * freshness + 0.2 * coverage + 0.2 * agreement
    return float(max(0.0, min(1.0, c)))


def uncertainty_band(expected_alpha: float, confidence: float) -> tuple[float, float]:
    width = (1.0 - confidence) * 8.0
    return expected_alpha - width, expected_alpha + width
