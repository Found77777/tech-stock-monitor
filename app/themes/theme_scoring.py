from __future__ import annotations

import math

from app.themes.policy_engine import policy_alignment_score
from app.themes.theme_classifier import classify_theme


def _safe(v, lo=0.0, hi=100.0) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return max(lo, min(hi, x))


def research_strength_score(row: dict) -> float:
    rd_ratio = _safe(row.get("rd_expense_ratio", 0), 0, 1)
    rd_head = _safe(row.get("rd_headcount_ratio", 0), 0, 1)
    phd = _safe(row.get("rd_phd_ratio", 0), 0, 1)
    master = _safe(row.get("rd_master_ratio", 0), 0, 1)
    continuity = _safe(row.get("rd_continuity_years", 0), 0, 10)

    if rd_ratio >= 0.15: base = 95
    elif rd_ratio >= 0.10: base = 85
    elif rd_ratio >= 0.05: base = 70
    elif rd_ratio >= 0.02: base = 50
    else: base = 20

    base += min(15, rd_head * 30)
    base += min(20, (phd + master) * 20)
    if continuity >= 3:
        base += 10
    return _safe(base)


def innovation_score(row: dict, primary_theme: str) -> float:
    invention = _safe(row.get("patent_invention_count", 0), 0, 100000)
    utility = _safe(row.get("patent_utility_count", 0), 0, 100000)
    growth3y = _safe(row.get("patent_growth_3y", 0), -1, 10)
    core_rel = _safe(row.get("patent_theme_relevance", 0.5), 0, 1)

    score = 30 + min(30, invention / 50) + min(10, utility / 200) + min(15, growth3y * 10) + core_rel * 15
    tech_keywords = ["AI芯片", "高速互联", "光通信", "机器人控制", "工业控制", "液冷", "半导体设备", "材料工艺"]
    text = str(row.get("core_patent_keywords", "")) + str(primary_theme)
    if any(k in text for k in tech_keywords):
        score += 8
    return _safe(score)


def industry_position_score(row: dict, primary_theme: str) -> float:
    market_share = _safe(row.get("market_share", 0), 0, 1)
    rd_rank_pct = _safe(row.get("rd_rank_pct", 0.5), 0, 1)
    chain_core = _safe(row.get("supply_chain_core", 0.4), 0, 1)
    domestic_key = _safe(row.get("domestic_substitution_key", 0.5), 0, 1)
    return _safe(25 + market_share * 30 + (1 - rd_rank_pct) * 20 + chain_core * 15 + domestic_key * 10)


def purity_score(row: dict, primary_theme: str) -> float:
    rev_ratio = _safe(row.get("theme_revenue_ratio", 0), 0, 1)
    concept = str(row.get("concept_purity", "related")).lower()
    concept_penalty = {"core": 0, "related": 8, "weak": 25, "hype": 40}.get(concept, 15)
    if rev_ratio > 0.5: base = 95
    elif rev_ratio > 0.2: base = 75
    elif rev_ratio > 0.05: base = 50
    else: base = 20
    return _safe(base - concept_penalty)


def evaluate_theme(row: dict) -> dict:
    cls = classify_theme(row)
    p_score = policy_alignment_score(cls["primary_theme"], row.get("policy_theme"))
    r_score = research_strength_score(row)
    i_score = innovation_score(row, cls["primary_theme"])
    pos_score = industry_position_score(row, cls["primary_theme"])
    pur_score = purity_score(row, cls["primary_theme"])
    theme_rel = _safe(0.2 * cls["theme_strength"] + 0.2 * p_score + 0.2 * pur_score + 0.2 * r_score + 0.1 * i_score + 0.1 * pos_score)
    return {
        "primary_theme": cls["primary_theme"],
        "secondary_theme": cls["secondary_theme"],
        "theme_strength": _safe(cls["theme_strength"]),
        "policy_alignment_score": _safe(p_score),
        "purity_score": _safe(pur_score),
        "innovation_score": _safe(i_score),
        "industry_position_score": _safe(pos_score),
        "research_strength_score": _safe(r_score),
        "theme_relevance_score": _safe(theme_rel),
    }
