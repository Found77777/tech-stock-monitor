import pandas as pd

from app.agent.sentiment_scorer import score_from_analysis
from app.data_sources.efinance_capital_flow import normalize_history_bill


def test_ai_sentiment_and_confidence_dynamic_with_news():
    positive = {
        "policy_sentiment": 80,
        "fundamental_event_score": 70,
        "industry_momentum": 60,
        "market_buzz_score": 80,
        "market_buzz_direction": 70,
        "macro_impact": 20,
        "composite_sentiment": 75,
        "confidence": 80,
        "_fetched_news_count": 5,
        "_source_success_counts": {"sina": 3, "eastmoney": 2},
        "_news_items": [{"title": "机器人政策利好 中标订单", "publish_time": "2026-06-01"} for _ in range(5)],
        "summary": "利好",
    }
    negative = {
        **positive,
        "policy_sentiment": -80,
        "fundamental_event_score": -90,
        "market_buzz_direction": -80,
        "composite_sentiment": -85,
        "_news_items": [{"title": "公司亏损 下修 减持 风险", "publish_time": "2026-06-01"} for _ in range(3)],
    }
    pos = score_from_analysis(positive)
    neg = score_from_analysis(negative)
    assert pos["ai_sentiment_score"] > 70
    assert neg["ai_sentiment_score"] < 30
    assert pos["ai_confidence"] != 30
    assert "AI评分依据" not in pos["ai_reason_summary"]
    assert "共抓取5条" in pos["ai_reason_summary"]


def test_no_news_only_case_keeps_neutral_low_confidence():
    out = score_from_analysis({"confidence": 0, "_fetched_news_count": 0, "_news_items": []})
    assert out["ai_sentiment_score"] == 50
    assert 10 <= out["ai_confidence"] <= 20


def test_efinance_capital_flow_confidence_varies_by_data_quality():
    full = pd.DataFrame({"日期": pd.date_range("2026-05-20", periods=10).strftime("%Y-%m-%d"), "主力净流入": [1_000_000 * i for i in range(1, 11)]})
    sparse = pd.DataFrame({"日期": ["2026-01-01", "2026-01-02"], "主力净流入": [1_000_000, -500_000]})
    a = normalize_history_bill(full, "600850")
    b = normalize_history_bill(sparse, "600850")
    assert a["capital_flow_confidence"] != b["capital_flow_confidence"]
    assert "最近10日净流入" in a["capital_flow_reason"]
