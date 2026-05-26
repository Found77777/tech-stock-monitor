from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from app.agent.prompts import BATCH_ANALYSIS_PROMPT, MARKET_OVERVIEW_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class NewsAgent:
    def __init__(self, settings: Any):
        self.settings = settings
        self.llm_api_key = getattr(settings, "llm_api_key", "")
        self.llm_base_url = getattr(settings, "llm_base_url", "https://api.openai.com/v1")
        self.llm_model = getattr(settings, "llm_model", "gpt-4o-mini")
        self.news_sources = _build_news_sources(settings)

    async def analyze_stocks(self, stock_codes: list[str]) -> list[dict]:
        news_items = await self._fetch_all_news(stock_codes)
        if not news_items:
            return []
        prompt = BATCH_ANALYSIS_PROMPT.format(stock_codes=", ".join(stock_codes), news_content=self._format_news(news_items))
        raw = await self._call_llm(prompt)
        parsed = self._parse_llm_response(raw)
        return parsed if isinstance(parsed, list) else []

    async def market_overview(self) -> dict:
        news_items = await self._fetch_market_news()
        raw = await self._call_llm(MARKET_OVERVIEW_PROMPT.format(market_content=self._format_news(news_items)))
        parsed = self._parse_llm_response(raw)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed:
            return parsed[0]
        return {}

    async def _fetch_all_news(self, stock_codes: list[str]) -> list[dict]:
        all_news: list[dict] = []
        for source in self.news_sources:
            try:
                all_news.extend(await source.fetch(stock_codes))
            except Exception:
                logger.exception("News source %s failed", source.name)
        return all_news

    async def _fetch_market_news(self) -> list[dict]:
        all_news: list[dict] = []
        for source in self.news_sources:
            try:
                all_news.extend(await source.fetch_market())
            except Exception:
                logger.exception("Market news source %s failed", source.name)
        return all_news

    async def _call_llm(self, user_prompt: str) -> str:
        if not self.llm_api_key:
            return "[]"
        headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}
        payload = {"model": self.llm_model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}], "temperature": 0.3, "max_tokens": 2048}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{self.llm_base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_llm_response(raw: str):
        cleaned = re.sub(r"```json\s*", "", raw)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            m = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except Exception:
                    return []
            return []

    @staticmethod
    def _format_news(items: list[dict]) -> str:
        if not items:
            return "暂无相关新闻。"
        return "\n".join([f"[{i+1}] 【{x.get('source','未知')}】{x.get('title','')} ({x.get('published','')})\n    {x.get('summary','')}" for i, x in enumerate(items[:50])])


class _BaseNewsSource:
    name = "base"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        return []

    async def fetch_market(self) -> list[dict]:
        return []


class SinaFinanceNews(_BaseNewsSource):
    name = "sina_finance"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items: list[dict] = []
        async with httpx.AsyncClient(timeout=15) as client:
            for code in stock_codes[:20]:
                try:
                    symbol = f"sh{code}" if str(code).startswith("6") else f"sz{code}"
                    url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{symbol}.phtml"
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        titles = re.findall(r'<a[^>]*href="(https?://finance\.sina[^"]*)"[^>]*>([^<]+)</a>', resp.text)
                        for link, title in titles[:5]:
                            items.append({"source": "新浪财经", "title": title.strip(), "summary": "", "url": link, "published": datetime.now().strftime("%Y-%m-%d"), "stock_code": code})
                except Exception:
                    continue
        return items


class EastMoneyNews(_BaseNewsSource):
    name = "eastmoney"


class XueqiuSentiment(_BaseNewsSource):
    name = "xueqiu"


def _build_news_sources(settings: Any) -> list[_BaseNewsSource]:
    enabled = {x.strip().lower() for x in str(getattr(settings, "agent_news_sources", "sina,eastmoney,xueqiu")).split(",")}
    sources: list[_BaseNewsSource] = []
    if "sina" in enabled:
        sources.append(SinaFinanceNews())
    if "eastmoney" in enabled:
        sources.append(EastMoneyNews())
    if "xueqiu" in enabled:
        sources.append(XueqiuSentiment())
    return sources or [SinaFinanceNews()]
