from __future__ import annotations

from datetime import datetime


def generate_signals(row: dict) -> list[dict]:
    out = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code, name = row["code"], row["name"]
    if row.get("new_20d_high") and row.get("volume_ratio_5d", 0) > 1.3:
        out.append({"code":code,"name":name,"signal_name":"volume_breakout","signal_type":"bullish","strength":80,"reason":"放量并创20日新高","generated_at":now})
    if row.get("drawdown_from_120d_high", 0) < -0.3 and row.get("distance_to_ma20", -1) > -0.02:
        out.append({"code":code,"name":name,"signal_name":"low_position_reversal","signal_type":"bullish","strength":65,"reason":"低位企稳迹象","generated_at":now})
    if row.get("distance_to_ma20", -1) > 0 and row.get("distance_to_ma60", -1) > 0:
        out.append({"code":code,"name":name,"signal_name":"trend_reclaim","signal_type":"bullish","strength":70,"reason":"重新站上MA20和MA60","generated_at":now})
    if row.get("excess_return_5d", -1) > 0 and row.get("excess_return_20d", -1) > 0:
        out.append({"code":code,"name":name,"signal_name":"relative_strength_turning_positive","signal_type":"bullish","strength":75,"reason":"相对强弱转正","generated_at":now})
    if row.get("stock_return_5d", 0) > 0.12 or row.get("distance_to_ma20", 0) > 0.15:
        out.append({"code":code,"name":name,"signal_name":"high_risk_overextended","signal_type":"bearish","strength":60,"reason":"短期涨幅过大或偏离均线过远","generated_at":now})
    if not row.get("is_liquid", True):
        out.append({"code":code,"name":name,"signal_name":"illiquid_warning","signal_type":"warning","strength":85,"reason":"流动性不足","generated_at":now})
    return out
