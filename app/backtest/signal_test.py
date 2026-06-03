from __future__ import annotations

import pandas as pd


def signal_event_study(signals: pd.DataFrame, bars: pd.DataFrame) -> list[dict]:
    b = bars.sort_values(["code", "trade_date"]).copy()
    b["fwd1"] = b.groupby("code")["close"].shift(-1) / b["close"] - 1
    b["fwd5"] = b.groupby("code")["close"].shift(-5) / b["close"] - 1
    b["fwd20"] = b.groupby("code")["close"].shift(-20) / b["close"] - 1
    merged = signals.merge(b[["code", "trade_date", "fwd1", "fwd5", "fwd20"]], on=["code", "trade_date"], how="left")
    out = []
    for sn, x in merged.groupby("signal_name"):
        out.append({
            "signal_name": sn,
            "samples": int(len(x)),
            "avg_return_1d": float(x["fwd1"].mean()),
            "avg_return_5d": float(x["fwd5"].mean()),
            "avg_return_20d": float(x["fwd20"].mean()),
            "win_rate_5d": float((x["fwd5"] > 0).mean()),
            "avg_excess_5d": float(x["fwd5"].mean()),
        })
    return out
