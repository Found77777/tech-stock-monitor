"""
改进的新闻数据源 - 使用官方 API 而不是爬虫
提高新闻抓取的可靠性和稳定性
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class _BaseNewsSource:
    name = "base"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        return []

    async def fetch_market(self) -> list[dict]:
        return []

    async def _get(self, client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
        resp = await client.get(url, **kwargs)
        logger.info("news_fetch source=%s url=%s status_code=%s", self.name, url, resp.status_code)
        return resp


class TushareNewsSource(_BaseNewsSource):
    """
    通过 Tushare 官方 API 获取新闻
    比爬虫更可靠、更稳定、不容易被封IP
    
    需要配置 TUSHARE_TOKEN 环境变量
    """
    name = "tushare"

    def __init__(self, tushare_token: str = ""):
        self.token = tushare_token

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        """从 Tushare 获取单个股票的新闻"""
        if not self.token:
            logger.warning("Tushare token not configured, skipping")
            return []

        items: list[dict] = []
        try:
            import tushare as ts
        except ImportError:
            logger.warning("tushare package not installed")
            return []

        try:
            pro = ts.pro_api(self.token)
            start_date = self._get_date_days_ago(7)

            for code in stock_codes[:20]:
                try:
                    # 标准化代码格式
                    ts_code = f"{code}.SH" if str(code).startswith("6") else f"{code}.SZ"

                    # 调用官方 API
                    df = pro.news(ts_code=ts_code, start_date=start_date, limit=15)

                    if df is not None and not df.empty:
                        for _, row in df.iterrows():
                            items.append({
                                "source": "Tushare",
                                "title": str(row.get("title", ""))[:200],
                                "summary": str(row.get("content", ""))[:300],
                                "url": str(row.get("url", "")),
                                "publish_time": str(row.get("ann_date", "")),
                                "stock_code": code,
                            })
                        logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, len(df))
                except Exception as e:
                    logger.exception("Tushare news fetch failed code=%s error=%s", code, e)

        except Exception as e:
            logger.exception("Tushare pro_api initialization failed: %s", e)

        return items

    async def fetch_market(self) -> list[dict]:
        """从 Tushare 获取市场整体新闻"""
        if not self.token:
            logger.warning("Tushare token not configured, skipping market news")
            return []

        items: list[dict] = []
        try:
            import tushare as ts
        except ImportError:
            logger.warning("tushare package not installed")
            return []

        try:
            pro = ts.pro_api(self.token)
            start_date = self._get_date_days_ago(3)

            # 获取市场整体新闻（不限制具体股票）
            df = pro.news(start_date=start_date, limit=20)

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    items.append({
                        "source": "Tushare市场新闻",
                        "title": str(row.get("title", ""))[:200],
                        "summary": str(row.get("content", ""))[:300],
                        "url": str(row.get("url", "")),
                        "publish_time": str(row.get("ann_date", "")),
                    })
                logger.info("news_parse source=%s parsed_market_news_count=%s", self.name, len(df))

        except Exception as e:
            logger.exception("Tushare market news fetch failed: %s", e)

        return items

    @staticmethod
    def _get_date_days_ago(days: int) -> str:
        """获取 N 天前的日期，格式为 YYYYMMDD"""
        return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")


class AkshareNewsSource(_BaseNewsSource):
    """
    通过 AKShare 库获取新闻
    作为 Tushare 的备选方案
    """
    name = "akshare"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        """从 AKShare 获取新闻"""
        items: list[dict] = []
        try:
            import akshare as ak
        except ImportError:
            logger.warning("akshare package not installed")
            return []

        for code in stock_codes[:20]:
            try:
                # AKShare 的新闻接口
                df = ak.stock_news_sina(symbol=code)

                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        items.append({
                            "source": "新浪财经(AKShare)",
                            "title": str(row.get("news_title", ""))[:200],
                            "summary": str(row.get("news_content", ""))[:300],
                            "url": str(row.get("news_url", "")),
                            "publish_time": str(row.get("ctime", "")),
                            "stock_code": code,
                        })
                    logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, len(df))

            except Exception as e:
                logger.exception("AKShare news fetch failed code=%s error=%s", code, e)

        return items

    async def fetch_market(self) -> list[dict]:
        """从 AKShare 获取市场新闻"""
        items: list[dict] = []
        try:
            import akshare as ak
        except ImportError:
            logger.warning("akshare package not installed")
            return []

        try:
            # AKShare 的市场新闻接口
            df = ak.stock_news_em()

            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    items.append({
                        "source": "东方财富市场新闻(AKShare)",
                        "title": str(row.get("title", ""))[:200],
                        "summary": str(row.get("summary", ""))[:300],
                        "url": str(row.get("url", "")),
                        "publish_time": str(row.get("time", "")),
                    })
                logger.info("news_parse source=%s parsed_market_news_count=%s", self.name, len(df))

        except Exception as e:
            logger.exception("AKShare market news fetch failed: %s", e)

        return items


def build_improved_news_sources(settings: Any) -> list[_BaseNewsSource]:
    """
    构建改进的新闻源列表
    优先使用官方 API（Tushare/AKShare），避免爬虫
    
    配置：
    - TUSHARE_TOKEN: Tushare API Token
    - AGENT_NEWS_SOURCES: 逗号分隔的源列表 (tushare,akshare)
    """
    enabled = {
        x.strip().lower()
        for x in str(getattr(settings, "agent_news_sources", "tushare,akshare")).split(",")
    }

    sources: list[_BaseNewsSource] = []

    # 优先级：Tushare > AKShare
    if "tushare" in enabled:
        tushare_token = str(getattr(settings, "tushare_token", "")).strip()
        if tushare_token:
            sources.append(TushareNewsSource(tushare_token))
            logger.info("Tushare news source enabled")
        else:
            logger.warning("Tushare token not configured, skipping Tushare source")

    if "akshare" in enabled:
        sources.append(AkshareNewsSource())
        logger.info("AKShare news source enabled")

    if not sources:
        logger.warning("No news sources enabled, using AKShare as fallback")
        sources.append(AkshareNewsSource())

    return sources
