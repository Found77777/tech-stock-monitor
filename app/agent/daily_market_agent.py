from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.agent.news_agent import NewsAgent
from app.universe.tech_universe import load_tech_universe_df


class DailyMarketIntelligenceAgent:
    def __init__(self, settings: Any):
        self.settings = settings
        self.news_agent = NewsAgent(settings)

    async def run(self, date: str | None = None, max_news: int = 5, max_related_stocks: int = 5) -> dict:
        max_news = max(1, min(int(max_news or 5), 5))
        max_related_stocks = max(1, min(int(max_related_stocks or 5), 5))
        candidate = await self._fetch_market_candidates(limit=10)
        if not candidate:
            return {
                "analysis_date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "top_news_json": [],
                "affected_sectors_json": [],
                "affected_themes_json": [],
                "related_stocks_json": [],
                "market_summary": "未抓取到有效市场新闻",
                "risk_notes": ["新闻源为空，未进行主题映射"],
            }

        analyzed = await self._analyze_news(candidate[:10])
        top_news = sorted(analyzed, key=lambda x: x.get("news_importance_score", 0), reverse=True)[:max_news]
        sectors = sorted({s for x in top_news for s in x.get("affected_sectors", [])})
        themes = sorted({s for x in top_news for s in x.get("affected_themes", [])})
        related = self._match_related_stocks(top_news, max_related_stocks=max_related_stocks)
        summary = f"近24小时筛选{len(top_news)}条关键新闻，涉及主题：{','.join(themes[:5]) if themes else '暂无'}"
        risks = ["仅基于公开新闻与规则映射，非投资建议"]
        return {
            "analysis_date": date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "top_news_json": top_news,
            "affected_sectors_json": sectors,
            "affected_themes_json": themes,
            "related_stocks_json": related,
            "market_summary": summary,
            "risk_notes": risks,
        }

    async def _fetch_market_candidates(self, limit: int = 10) -> list[dict]:
        items = await self.news_agent._fetch_market_news()
        return items[:limit]

    async def _analyze_news(self, news_items: list[dict]) -> list[dict]:
        # LLM analyzes only news; no per-stock LLM calls.
        if not self.news_agent.llm_api_key:
            return [self._rule_news_eval(x) for x in news_items]
        prompt = (
            "你是A股市场情报分析助手。请从新闻中提取影响信息，输出JSON数组。每条格式："
            '{"title":"","news_importance_score":0-100,"affected_sectors":[],"affected_themes":[],"impact_direction":"positive|negative|neutral","impact_horizon":"intraday|short_term|medium_term","reason":""}\n'
            f"新闻列表：{json.dumps(news_items[:10], ensure_ascii=False)}"
        )
        raw = await self.news_agent._call_llm(prompt)
        parsed = self.news_agent._parse_llm_response(raw)
        if isinstance(parsed, list) and parsed:
            out = []
            by_title = {str(x.get("title", "")): x for x in news_items}
            for x in parsed:
                title = str(x.get("title", ""))
                src = by_title.get(title, {})
                out.append(
                    {
                        "title": title or str(src.get("title", "")),
                        "url": src.get("url", ""),
                        "source": src.get("source", ""),
                        "publish_time": src.get("publish_time", ""),
                        "summary": src.get("summary", ""),
                        "news_importance_score": int(max(0, min(100, float(x.get("news_importance_score", 50))))),
                        "affected_sectors": x.get("affected_sectors", []) or [],
                        "affected_themes": x.get("affected_themes", []) or [],
                        "impact_direction": x.get("impact_direction", "neutral"),
                        "impact_horizon": x.get("impact_horizon", "short_term"),
                        "reason": x.get("reason", ""),
                    }
                )
            return out
        return [self._rule_news_eval(x) for x in news_items]

    def _rule_news_eval(self, item: dict) -> dict:
        txt = f"{item.get('title','')} {item.get('summary','')}"
        score = 50
        themes = []
        sectors = []
        for kw, th in [("算力", "AI算力"), ("数据中心", "数据中心"), ("半导体", "半导体设备"), ("机器人", "机器人"), ("信创", "信创"), ("液冷", "液冷")]:
            if kw in txt:
                score += 8
                themes.append(th)
        for sk in ["电子", "计算机", "通信", "半导体", "软件"]:
            if sk in txt:
                sectors.append(sk)
        direction = "negative" if any(x in txt for x in ["下滑", "处罚", "风险", "下跌"]) else "positive"
        return {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", ""),
            "publish_time": item.get("publish_time", ""),
            "summary": item.get("summary", ""),
            "news_importance_score": max(0, min(100, score)),
            "affected_sectors": sorted(set(sectors)),
            "affected_themes": sorted(set(themes)),
            "impact_direction": direction,
            "impact_horizon": "short_term",
            "reason": "规则引擎映射",
        }

    def _match_related_stocks(self, top_news: list[dict], max_related_stocks: int = 5) -> list[dict]:
        u = load_tech_universe_df()
        score_map: dict[str, dict] = {}
        for _, row in u.iterrows():
            code = str(row.get("code", ""))
            name = str(row.get("name", ""))
            sector = str(row.get("sector", ""))
            theme = str(row.get("theme", ""))
            policy_theme = str(row.get("policy_theme", ""))
            matched_themes = []
            matched_titles = []
            rel = 0.0
            for n in top_news:
                ns = " ".join([*(n.get("affected_sectors", []) or []), *(n.get("affected_themes", []) or [])])
                if sector and sector in ns:
                    rel += 12
                    matched_titles.append(n.get("title", ""))
                for t in (n.get("affected_themes", []) or []):
                    if t and (t in theme or t in policy_theme):
                        rel += 20
                        matched_themes.append(t)
                        matched_titles.append(n.get("title", ""))
            if rel > 0:
                score_map[code] = {
                    "code": code,
                    "name": name,
                    "relevance_score": min(100.0, rel),
                    "matched_themes": sorted(set(matched_themes)),
                    "matched_news_titles": sorted(set([x for x in matched_titles if x])),
                    "reason": "基于 sector/theme/policy_theme 规则匹配",
                }
        rows = sorted(score_map.values(), key=lambda x: x["relevance_score"], reverse=True)
        return rows[:max_related_stocks]
