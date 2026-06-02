from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.agent.performance import AgentPerformanceMonitor
from app.agent.prompts import BATCH_ANALYSIS_PROMPT, MARKET_OVERVIEW_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class NewsAgent:
    def __init__(self, settings: Any):
        self.settings = settings
        self.llm_api_key = getattr(settings, "llm_api_key", "")
        self.llm_base_url = getattr(settings, "llm_base_url", "https://api.openai.com/v1")
        self.llm_model = getattr(settings, "llm_model", "gpt-4o-mini")
        self.llm_http_proxy = str(getattr(settings, "llm_http_proxy", "") or "").strip()
        self.news_sources = _build_news_sources(settings)
        self.last_source_debug: dict[str, Any] = {}
        self.last_llm_status = "not_called"
        self.last_llm_error = ""
        self.last_llm_latency_ms = 0.0


    def _build_client_kwargs(self, timeout: float, use_llm_proxy: bool = False) -> dict:
        kwargs: dict[str, Any] = {"timeout": timeout, "trust_env": False}
        if use_llm_proxy and self.llm_http_proxy:
            kwargs["proxy"] = self.llm_http_proxy
        return kwargs

    def _create_async_client(self, timeout: float, use_llm_proxy: bool = False) -> httpx.AsyncClient:
        kwargs = self._build_client_kwargs(timeout=timeout, use_llm_proxy=use_llm_proxy)
        try:
            return httpx.AsyncClient(**kwargs)
        except TypeError:
            if "proxy" in kwargs:
                proxy = kwargs.pop("proxy")
                kwargs["proxies"] = {"http://": proxy, "https://": proxy}
            return httpx.AsyncClient(**kwargs)

    async def analyze_stocks(self, stock_codes: list[str]) -> list[dict]:
        monitor = AgentPerformanceMonitor()
        with monitor.measure("fetch_all_news"):
            news_items = await self._fetch_all_news(stock_codes)
        self.last_source_debug["performance_ms"] = monitor.as_debug()
        if not news_items:
            self.last_llm_status = "skipped_no_news"
            return []
        prompt = BATCH_ANALYSIS_PROMPT.format(stock_codes=", ".join(stock_codes), news_content=self._format_news(news_items))
        try:
            raw = await self._call_llm(prompt)
            parsed = self._parse_llm_response(raw)
            if isinstance(parsed, list) and parsed:
                self.last_llm_status = "ok"
                return parsed
            self.last_llm_status = "parse_failed"
            self.last_llm_error = "LLM response did not parse into a non-empty list"
            logger.warning("llm_parse_failed scope=stock_analysis stock_codes=%s raw_preview=%s", stock_codes, str(raw)[:300])
        except Exception as exc:
            self.last_llm_status = "call_failed"
            self.last_llm_error = f"{type(exc).__name__}: {exc}"
            logger.exception("llm_call_failed scope=stock_analysis stock_codes=%s error_type=%s", stock_codes, type(exc).__name__)
        return self._fallback_stock_analyses(stock_codes, news_items)

    async def market_overview(self) -> dict:
        news_items = await self._fetch_market_news()
        try:
            raw = await self._call_llm(MARKET_OVERVIEW_PROMPT.format(market_content=self._format_news(news_items)))
            parsed = self._parse_llm_response(raw)
            if isinstance(parsed, dict):
                self.last_llm_status = "ok"
                return parsed
            if isinstance(parsed, list) and parsed:
                self.last_llm_status = "ok"
                return parsed[0]
            self.last_llm_status = "parse_failed"
            logger.warning("llm_parse_failed scope=market_overview raw_preview=%s", str(raw)[:300])
        except Exception as exc:
            self.last_llm_status = "call_failed"
            self.last_llm_error = f"{type(exc).__name__}: {exc}"
            logger.exception("llm_call_failed scope=market_overview error_type=%s", type(exc).__name__)
        return self._fallback_market_overview(news_items)

    async def _fetch_all_news(self, stock_codes: list[str]) -> list[dict]:
        all_news: list[dict] = []
        source_success_counts: dict[str, int] = {}
        source_errors: dict[str, str] = {}
        for code in stock_codes:
            code_news, debug = await self.fetch_stock_news(str(code))
            all_news.extend(code_news)
            for k, v in (debug.get("source_success_counts", {}) or {}).items():
                source_success_counts[k] = source_success_counts.get(k, 0) + int(v)
            for k, v in (debug.get("source_errors", {}) or {}).items():
                source_errors[k] = v
        self.last_source_debug = {
            "source_success_counts": source_success_counts,
            "source_errors": source_errors,
            "final_return_count": len(all_news),
        }
        return all_news

    async def fetch_stock_news(self, code: str) -> tuple[list[dict], dict]:
        all_news: list[dict] = []
        source_success_counts: dict[str, int] = {}
        source_errors: dict[str, str] = {}
        for source in self.news_sources:
            try:
                got = await source.fetch([code])
                cnt = len(got or [])
                if cnt > 0:
                    source_success_counts[source.name] = source_success_counts.get(source.name, 0) + cnt
                    all_news.extend(got)
            except Exception as exc:
                source_errors[source.name] = f"{type(exc).__name__}: {exc}"
                logger.exception("news_source_failed source=%s code=%s error_type=%s", source.name, code, type(exc).__name__)
        before = len(all_news)
        normalized = _normalize_news_items(all_news)
        deduped = _dedup_news(normalized)
        after = len(deduped)
        if after == 0:
            if before == 0 and source_errors:
                reason = "source_errors_only"
            elif before == 0:
                reason = "all_sources_empty"
            else:
                reason = "parsed_but_filtered_out"
        else:
            reason = "ok"
        debug = {
            "code": code,
            "source_success_counts": source_success_counts,
            "source_errors": source_errors,
            "total_before_dedupe": before,
            "total_after_dedupe": after,
            "final_return_count": after,
            "debug_reason": reason,
            "final_news": deduped[:10],
        }
        logger.info("stock_news_aggregate code=%s source_success_counts=%s total_before_dedupe=%s total_after_dedupe=%s final_return_count=%s debug_reason=%s",
                    code, source_success_counts, before, after, after, reason)
        return deduped, debug

    async def _fetch_market_news(self) -> list[dict]:
        all_news: list[dict] = []
        for source in self.news_sources:
            try:
                all_news.extend(await source.fetch_market())
            except Exception:
                logger.exception("Market news source %s failed", source.name)
        return _dedup_news(_normalize_news_items(all_news))

    async def _call_llm(self, user_prompt: str) -> str:
        if not self.llm_api_key:
            return "[]"
        headers = {"Authorization": f"Bearer {self.llm_api_key}", "Content-Type": "application/json"}
        payload = {"model": self.llm_model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}], "temperature": 0.3, "max_tokens": 2048}
        import time
        started = time.perf_counter()
        async with self._create_async_client(timeout=60, use_llm_proxy=True) as client:
            resp = await client.post(f"{self.llm_base_url}/chat/completions", headers=headers, json=payload)
            self.last_llm_latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info("llm_response status_code=%s latency_ms=%.2f model=%s", resp.status_code, self.last_llm_latency_ms, self.llm_model)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _fallback_stock_analyses(self, stock_codes: list[str], news_items: list[dict]) -> list[dict]:
        analyses: list[dict] = []
        positive_words = ["中标", "订单", "预增", "突破", "利好", "签约", "政策", "补贴"]
        negative_words = ["处罚", "减持", "诉讼", "预亏", "下修", "风险", "亏损"]
        for code in stock_codes:
            code_items = [x for x in news_items if str(x.get("stock_code", "")) in {"", str(code)}]
            if not code_items:
                continue
            text = " ".join(f"{x.get('title','')} {x.get('summary','')}" for x in code_items[:5])
            pos = sum(text.count(w) for w in positive_words)
            neg = sum(text.count(w) for w in negative_words)
            composite = max(-60, min(60, (pos - neg) * 18))
            confidence = max(10, min(55, 15 + len(code_items) * 5 + (pos + neg) * 5))
            risk_flags = [w for w in negative_words if w in text][:3]
            analyses.append({
                "stock_code": str(code).zfill(6)[-6:],
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "policy_sentiment": 20 if "政策" in text or "补贴" in text else 0,
                "fundamental_event_score": max(-60, min(60, (pos - neg) * 15)),
                "industry_momentum": 0,
                "market_buzz_score": min(100, len(code_items) * 10),
                "market_buzz_direction": composite,
                "macro_impact": 0,
                "composite_sentiment": composite,
                "confidence": confidence,
                "key_events": [x.get("title", "") for x in code_items[:3] if x.get("title")],
                "risk_flags": risk_flags,
                "summary": "LLM不可用，已基于规则引擎从已抓取新闻生成兜底分析",
                "llm_fallback": True,
            })
        logger.info("rule_based_stock_analysis generated_count=%s stock_codes=%s", len(analyses), stock_codes)
        return analyses

    def _fallback_market_overview(self, news_items: list[dict]) -> dict:
        text = " ".join(f"{x.get('title','')} {x.get('summary','')}" for x in news_items[:10])
        policy_hits = sum(text.count(w) for w in ["政策", "国务院", "工信部", "补贴"])
        risk_hits = sum(text.count(w) for w in ["风险", "下跌", "处罚", "监管"])
        sentiment = max(-40, min(40, policy_hits * 10 - risk_hits * 10))
        return {
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "market_sentiment": sentiment,
            "tech_sector_sentiment": sentiment,
            "policy_direction": "偏多" if policy_hits > risk_hits else "中性",
            "key_themes": [],
            "macro_risks": ["LLM不可用，市场概览使用规则兜底"],
            "summary": "LLM不可用，已使用规则引擎生成市场概览",
            "llm_fallback": True,
        }

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
        return "\n".join([f"[{i+1}] 【{x.get('source','未知')}】{x.get('title','')} ({x.get('publish_time','')})\n    {x.get('summary','')}" for i, x in enumerate(items[:50])])


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


class SinaFinanceNews(_BaseNewsSource):
    name = "sina_finance"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items: list[dict] = []
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            for code in stock_codes[:20]:
                symbol = f"sh{code}" if str(code).startswith("6") else f"sz{code}"
                url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{symbol}.phtml"
                try:
                    resp = await self._get(client, url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        titles = re.findall(r'<a[^>]*href="(https?://finance\.sina[^\"]*)"[^>]*>([^<]+)</a>', resp.text)
                        for link, title in titles[:8]:
                            items.append({"source": "新浪财经", "title": title.strip(), "summary": "", "url": link, "publish_time": datetime.now().strftime("%Y-%m-%d"), "stock_code": code})
                        logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, len(titles[:8]))
                except Exception:
                    logger.exception("Sina news fetch failed code=%s", code)
        return items

    async def fetch_market(self) -> list[dict]:
        items: list[dict] = []
        url = "https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=20&zhibo_id=152"
        try:
            async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
                resp = await self._get(client, url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    feeds = data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
                    for feed in feeds:
                        items.append({"source": "新浪7x24", "title": (feed.get("rich_text", "") or "")[:120], "summary": "", "url": "", "publish_time": feed.get("create_time", "")})
                    logger.info("news_parse source=%s parsed_news_count=%s", self.name, len(items))
        except Exception:
            logger.exception("Sina market news fetch failed")
        return items


class EastMoneyNews(_BaseNewsSource):
    name = "eastmoney"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items: list[dict] = []
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            for code in stock_codes[:20]:
                query = quote(code)
                article_url = f"https://search-api-web.eastmoney.com/search/jsonp?cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{query}%22%2C%22type%22%3A%5B%22cmsArticleWebOld%22%2C%22stock_notice%22%5D%2C%22pageIndex%22%3A1%2C%22pageSize%22%3A8%7D"
                try:
                    resp = await self._get(client, article_url, headers={"User-Agent": "Mozilla/5.0"})
                    parsed_count = 0
                    if resp.status_code == 200:
                        m = re.search(r"jQuery\((.*)\)", resp.text, re.DOTALL)
                        if m:
                            data = json.loads(m.group(1))
                            for article in data.get("result", []) or []:
                                if not isinstance(article, dict):
                                    continue
                                items.append({"source": "东方财富", "title": article.get("title", ""), "summary": (article.get("content", "") or "")[:220], "url": article.get("url", ""), "publish_time": article.get("date", ""), "stock_code": code})
                                parsed_count += 1
                    logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, parsed_count)
                except Exception:
                    logger.exception("EastMoney news fetch failed code=%s", code)
        return items


class CninfoNews(_BaseNewsSource):
    name = "cninfo"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items: list[dict] = []
        url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/plain, */*",
            "Origin": "http://www.cninfo.com.cn",
            "Referer": "http://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search&checkedCategory=category_ndbg_szsh;",
        }
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            for code in stock_codes[:20]:
                try:
                    data = {
                        "stock": f"{code},gssh",
                        "tabName": "fulltext",
                        "pageSize": 8,
                        "pageNum": 1,
                        "column": "szse",
                        "plate": "",
                        "searchkey": "",
                        "secid": "",
                        "category": "",
                    }
                    resp = await client.post(url, headers=headers, data=data)
                    logger.info("news_fetch source=%s url=%s status_code=%s", self.name, url, resp.status_code)
                    parsed_count = 0
                    if resp.status_code == 200:
                        body = resp.json()
                        anns = body.get("announcements") or []
                        for ann in anns:
                            adjs = ann.get("adjunctUrl", "")
                            full_url = f"http://static.cninfo.com.cn/{adjs}" if adjs else ""
                            items.append({"source": "巨潮资讯", "title": ann.get("announcementTitle", ""), "summary": ann.get("announcementTitle", ""), "url": full_url, "publish_time": ann.get("announcementTime", ""), "stock_code": code})
                            parsed_count += 1
                    logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, parsed_count)
                except Exception:
                    logger.exception("Cninfo fetch failed code=%s", code)
        return items


class BaiduNewsFallback(_BaseNewsSource):
    name = "baidu_news"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items: list[dict] = []
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            for code in stock_codes[:20]:
                q = quote(f"{code} 股票")
                url = f"https://news.baidu.com/ns?word={q}&tn=news&from=news&cl=2&rn=8"
                try:
                    resp = await self._get(client, url, headers={"User-Agent": "Mozilla/5.0"})
                    parsed_count = 0
                    if resp.status_code == 200:
                        matches = re.findall(r'<h3 class="news-title_1YtI1">\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
                        for link, title_html in matches[:8]:
                            title = re.sub(r"<.*?>", "", title_html).strip()
                            items.append({"source": "百度新闻", "title": title, "summary": "", "url": link, "publish_time": datetime.now().strftime("%Y-%m-%d"), "stock_code": code})
                            parsed_count += 1
                    logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, parsed_count)
                except Exception:
                    logger.exception("Baidu fallback failed code=%s", code)
        return items


class RssNewsFallback(_BaseNewsSource):
    name = "rss_fallback"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items: list[dict] = []
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            for code in stock_codes[:20]:
                q = quote(f"{code} A股")
                url = f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
                try:
                    resp = await self._get(client, url, headers={"User-Agent": "Mozilla/5.0"})
                    parsed_count = 0
                    if resp.status_code == 200:
                        for title in re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", resp.text)[1:9]:
                            items.append({"source": "RSS", "title": title.strip(), "summary": "", "url": "", "publish_time": datetime.now().strftime("%Y-%m-%d"), "stock_code": code})
                            parsed_count += 1
                    logger.info("news_parse source=%s code=%s parsed_news_count=%s", self.name, code, parsed_count)
                except Exception:
                    logger.exception("RSS fallback failed code=%s", code)
        return items


def _normalize_news_items(items: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        normalized.append({
            "title": str(item.get("title", "")).strip(),
            "url": str(item.get("url", "")).strip(),
            "source": str(item.get("source", "未知")).strip() or "未知",
            "publish_time": str(item.get("publish_time") or item.get("published") or "").strip(),
            "summary": str(item.get("summary", "")).strip(),
            "stock_code": str(item.get("stock_code", "")).strip(),
        })
    return [x for x in normalized if x["title"]]


def _dedup_news(items: list[dict]) -> list[dict]:
    seen_title: set[str] = set()
    seen_url: set[str] = set()
    out: list[dict] = []
    for item in items:
        title_key = item.get("title", "").strip().lower()
        url_key = item.get("url", "").strip().lower()
        if title_key and title_key in seen_title:
            continue
        if url_key and url_key in seen_url:
            continue
        if title_key:
            seen_title.add(title_key)
        if url_key:
            seen_url.add(url_key)
        out.append(item)
    return out


def _build_news_sources(settings: Any) -> list[_BaseNewsSource]:
    enabled = {x.strip().lower() for x in str(getattr(settings, "agent_news_sources", "sina,eastmoney,cninfo,baidu,rss")).split(",")}
    sources: list[_BaseNewsSource] = []
    if "sina" in enabled:
        sources.append(SinaFinanceNews())
    if "eastmoney" in enabled:
        sources.append(EastMoneyNews())
    if "cninfo" in enabled:
        sources.append(CninfoNews())
    if "baidu" in enabled:
        sources.append(BaiduNewsFallback())
    if "rss" in enabled:
        sources.append(RssNewsFallback())
    return sources or [SinaFinanceNews(), EastMoneyNews(), CninfoNews(), BaiduNewsFallback(), RssNewsFallback()]
