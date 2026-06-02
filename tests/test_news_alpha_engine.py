from datetime import datetime, timedelta, timezone

from app.agent.news_alpha_engine import compute_news_alpha, score_news_freshness, score_news_relevance


def test_relevance_company_hit_higher_than_generic():
    md = {"code": "002465", "name": "海格通信", "theme": "卫星"}
    direct = {"title": "海格通信002465中标重大订单", "summary": ""}
    generic = {"title": "卫星板块异动", "summary": ""}
    assert score_news_relevance(direct, md) > score_news_relevance(generic, md)


def test_freshness_today_higher_than_old():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old = (datetime.now(timezone.utc) - timedelta(days=11)).strftime("%Y-%m-%d")
    f1, _ = score_news_freshness({"publish_time": today})
    f2, _ = score_news_freshness({"publish_time": old})
    assert f1 > f2


def test_market_noise_cap_and_risk_negative_and_no_news_zero():
    md = {"code": "002465", "name": "海格通信"}
    noise_items = [{"title": "板块异动 短线情绪升温", "summary": "", "publish_time": datetime.now(timezone.utc).strftime('%Y-%m-%d')} for _ in range(5)]
    out = compute_news_alpha(noise_items, md)
    assert out["news_alpha_adjustment"] <= 2

    risk_items = [{"title": "海格通信被处罚并涉诉讼", "summary": "", "publish_time": datetime.now(timezone.utc).strftime('%Y-%m-%d')}]
    out2 = compute_news_alpha(risk_items, md)
    assert out2["news_alpha_adjustment"] < 0

    out3 = compute_news_alpha([], md)
    assert out3["news_alpha_adjustment"] == 0
