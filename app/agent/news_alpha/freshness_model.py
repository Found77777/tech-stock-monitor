from __future__ import annotations

from datetime import datetime, timezone
from math import exp


def freshness_score(publish_time: str | None, half_life_days: float = 3.0) -> float:
    if not publish_time:
        return 50.0
    try:
        d = datetime.fromisoformat(str(publish_time)[:19]).replace(tzinfo=timezone.utc)
    except Exception:
        try:
            d = datetime.fromisoformat(str(publish_time)[:10]).replace(tzinfo=timezone.utc)
        except Exception:
            return 50.0
    days = max(0.0, (datetime.now(timezone.utc) - d).total_seconds() / 86400)
    return float(max(5.0, min(100.0, 100.0 * exp(-days / max(half_life_days, 0.5)))))
