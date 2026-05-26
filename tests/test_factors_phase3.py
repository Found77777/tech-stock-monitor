import pandas as pd

from app.factors.technical import add_technical_factors


def test_ma_and_volume_ratio():
    df = pd.DataFrame({"trade_date": [f"2026-01-{i:02d}" for i in range(1, 31)], "close": list(range(1, 31)), "volume": [100]*30, "amount": [1000]*30, "turnover_rate": [1]*30})
    out = add_technical_factors(df)
    assert round(out.iloc[-1]["ma20"], 2) == 20.5
    assert round(out.iloc[-1]["volume_ratio_5d"], 2) == 1.0
