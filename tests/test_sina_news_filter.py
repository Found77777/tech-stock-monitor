import asyncio

from app.agent.news_agent import NewsAgent, _reject_reason_for_company_news
from app.config import get_settings


class StaticSina:
    name = "sina_finance"

    async def fetch(self, stock_codes):
        code = stock_codes[0]
        return [
            {"source": "新浪财经", "title": "财经首页", "summary": "", "url": "u-nav-1", "publish_time": "2026-05-27", "stock_code": code},
            {"source": "新浪财经", "title": "股票", "summary": "", "url": "u-nav-2", "publish_time": "2026-05-27", "stock_code": code},
            {"source": "新浪财经", "title": "基金", "summary": "", "url": "u-nav-3", "publish_time": "2026-05-27", "stock_code": code},
            {"source": "新浪财经", "title": "港股", "summary": "", "url": "u-nav-4", "publish_time": "2026-05-27", "stock_code": code},
            {"source": "新浪财经", "title": "机器人行业政策催化", "summary": "行业新闻但不含公司实体", "url": "u-generic", "publish_time": "2026-05-27", "stock_code": code},
            {"source": "新浪财经", "title": "中大力德002896机器人减速器订单增长", "summary": "中大力德产能释放", "url": "u-company", "publish_time": "2026-05-27", "stock_code": code},
        ]

    async def fetch_market(self):
        return []


class NavOnlySina(StaticSina):
    async def fetch(self, stock_codes):
        code = stock_codes[0]
        return [
            {"source": "新浪财经", "title": title, "summary": "", "url": f"u-{i}", "publish_time": "2026-05-27", "stock_code": code}
            for i, title in enumerate(["财经首页", "股票", "基金", "港股", "美股"])
        ]


def test_sina_navigation_titles_are_rejected_with_reasons():
    assert _reject_reason_for_company_news({"title": "财经首页", "summary": ""}, "002896") == "navigation_menu"
    for title in ["股票", "基金", "港股", "美股"]:
        assert _reject_reason_for_company_news({"title": title, "summary": ""}, "002896") == "generic_channel"


def test_sina_news_filter_keeps_only_company_level_news():
    agent = NewsAgent(get_settings())
    agent.news_sources = [StaticSina()]

    items, debug = asyncio.run(agent.fetch_stock_news("002896"))

    assert debug["raw_news_count"] == 6
    assert debug["filtered_news_count"] == 1
    assert debug["valid_news_count"] == 1
    assert debug["rejected_reason"]["navigation_menu"] == 1
    assert debug["rejected_reason"]["generic_channel"] == 3
    assert debug["rejected_reason"]["no_company_entity"] == 1
    assert [x["title"] for x in items] == ["中大力德002896机器人减速器订单增长"]


def test_sina_news_filter_returns_empty_when_no_company_news():
    agent = NewsAgent(get_settings())
    agent.news_sources = [NavOnlySina()]

    items, debug = asyncio.run(agent.fetch_stock_news("002896"))

    assert items == []
    assert debug["raw_news_count"] == 5
    assert debug["valid_news_count"] == 0
    assert debug["debug_reason"] == "no_company_level_news"
    assert debug["message"] == "未找到公司级新闻。"
