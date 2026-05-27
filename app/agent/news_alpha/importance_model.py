from __future__ import annotations

BASE = {
    "company_order": 90,
    "earnings": 85,
    "policy_catalyst": 80,
    "product_launch": 72,
    "capex": 68,
    "financing": 55,
    "governance": 45,
    "risk_event": 88,
    "litigation": 82,
    "export_control": 78,
    "subsidy": 75,
    "market_noise": 20,
    "unknown": 30,
}


def importance_score(event_type: str) -> float:
    return float(BASE.get(event_type, 30))
