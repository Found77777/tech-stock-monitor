import pandas as pd

from app.factors.technical import add_technical_factors


def test_ma_and_volume_ratio():
    df = pd.DataFrame({"trade_date": [f"2026-01-{i:02d}" for i in range(1, 31)], "close": list(range(1, 31)), "volume": [100]*30, "amount": [1000]*30, "turnover_rate": [1]*30})
    out = add_technical_factors(df)
    assert round(out.iloc[-1]["ma20"], 2) == 20.5
    assert round(out.iloc[-1]["volume_ratio_5d"], 2) == 1.0


def test_low_position_structure_fields_exist():
    df = pd.DataFrame({
        "trade_date": [f"2025-01-{(i%28)+1:02d}" for i in range(1, 301)],
        "close": [100 + (i * 0.05) for i in range(300)],
        "volume": [1000 + (i % 7) * 10 for i in range(300)],
        "amount": [100000 + (i % 9) * 500 for i in range(300)],
        "turnover_rate": [1.0] * 300,
    })
    out = add_technical_factors(df)
    for c in ["drawdown_from_250d_high", "percentile_250d", "consolidation_days", "ma_structure_score", "trend_reversal_score"]:
        assert c in out.columns
