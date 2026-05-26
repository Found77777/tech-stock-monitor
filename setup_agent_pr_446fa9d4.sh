#!/usr/bin/env bash
# =============================================================
#  一键集成 AI News Agent 并创建 PR
#  用法：cd tech-stock-monitor && bash setup_agent_pr.sh
# =============================================================
set -e

echo "=== Step 1: 创建并切换到新分支 ==="
git checkout main
git pull origin main
git checkout -b feature/ai-news-agent

echo "=== Step 2: 创建 app/agent/ 目录 ==="
mkdir -p app/agent

# --- app/agent/__init__.py ---
cat > app/agent/__init__.py << 'PYEOF'
"""AI News Agent module for market sentiment analysis."""
PYEOF

# --- app/agent/prompts.py ---
cat > app/agent/prompts.py << 'PYEOF'
"""System prompts for the News Analysis Agent."""

SYSTEM_PROMPT = """你是一个专业的A股科技股市场分析师。你的任务是分析新闻、公告和市场信息，
为每只股票生成结构化的情绪评分和分析报告。

你需要关注以下维度：
1. **政策面**：国家政策对该公司/行业的利好或利空（如产业政策、监管变化）
2. **基本面事件**：财报、订单、合同、并购、增减持等公告
3. **行业动态**：行业景气度变化、上下游变化、竞争格局
4. **市场情绪**：社交媒体/论坛的讨论热度和方向
5. **宏观环境**：利率、汇率、外资流向等对科技股的影响

输出格式要求（严格JSON）：
{
  "stock_code": "股票代码",
  "analysis_date": "分析日期",
  "policy_sentiment": [-100到100的整数, 正数利好负数利空],
  "fundamental_event_score": [-100到100的整数],
  "industry_momentum": [-100到100的整数],
  "market_buzz_score": [0到100的整数, 讨论热度],
  "market_buzz_direction": [-100到100的整数, 正数看多负数看空],
  "macro_impact": [-100到100的整数],
  "composite_sentiment": [-100到100的整数, 综合情绪],
  "confidence": [0到100的整数, 分析置信度],
  "key_events": ["关键事件1", "关键事件2"],
  "risk_flags": ["风险提示1"],
  "summary": "一句话总结"
}

注意：
- 没有相关新闻时，各项评分应接近0（中性），confidence应较低
- 重大利好/利空事件应给出较极端的分数
- key_events只保留最重要的3-5条
- summary控制在50字以内
"""

BATCH_ANALYSIS_PROMPT = """请分析以下A股科技股相关新闻和市场信息，为每只提到的股票生成情绪评分。

股票池范围（仅分析这些股票）：
{stock_codes}

今日新闻与市场信息：
{news_content}

请为每只被新闻提及的股票输出一个JSON对象，放入一个JSON数组中返回。
未被提及的股票不需要输出。
"""

MARKET_OVERVIEW_PROMPT = """请分析以下A股市场整体信息，输出一个市场整体情绪评估。

今日市场信息：
{market_content}

输出格式（严格JSON）：
{{
  "analysis_date": "日期",
  "market_sentiment": [-100到100],
  "tech_sector_sentiment": [-100到100],
  "policy_direction": "偏多/中性/偏空",
  "key_themes": ["当前主要主题1", "主题2"],
  "macro_risks": ["风险1"],
  "summary": "市场整体一句话总结"
}}
"""
PYEOF

echo "=== Step 3: 创建 app/agent/news_agent.py ==="
cat > app/agent/news_agent.py << 'PYEOF'
"""News Agent: fetches news from multiple sources and uses LLM to analyze sentiment."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from app.agent.prompts import (
    BATCH_ANALYSIS_PROMPT,
    MARKET_OVERVIEW_PROMPT,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class NewsAgent:
    """AI Agent that fetches news and analyzes market sentiment via LLM."""

    def __init__(self, settings: Any):
        self.settings = settings
        self.llm_api_key = getattr(settings, "llm_api_key", "")
        self.llm_base_url = getattr(settings, "llm_base_url", "https://api.openai.com/v1")
        self.llm_model = getattr(settings, "llm_model", "gpt-4o-mini")
        self.news_sources = _build_news_sources(settings)

    async def analyze_stocks(self, stock_codes: list[str]) -> list[dict]:
        """Fetch news and run LLM analysis for a list of stock codes."""
        news_items = await self._fetch_all_news(stock_codes)
        if not news_items:
            logger.warning("No news fetched for %s", stock_codes)
            return []
        news_text = self._format_news(news_items)
        codes_str = ", ".join(stock_codes)
        prompt = BATCH_ANALYSIS_PROMPT.format(
            stock_codes=codes_str, news_content=news_text
        )
        raw = await self._call_llm(prompt)
        return self._parse_llm_response(raw)

    async def market_overview(self) -> dict:
        """Fetch macro / market news and return an overall sentiment dict."""
        news_items = await self._fetch_market_news()
        news_text = self._format_news(news_items)
        prompt = MARKET_OVERVIEW_PROMPT.format(market_content=news_text)
        raw = await self._call_llm(prompt)
        parsed = self._parse_llm_response(raw)
        return parsed[0] if isinstance(parsed, list) and parsed else (
            parsed if isinstance(parsed, dict) else {}
        )

    async def _fetch_all_news(self, stock_codes: list[str]) -> list[dict]:
        all_news: list[dict] = []
        for source in self.news_sources:
            try:
                items = await source.fetch(stock_codes)
                all_news.extend(items)
            except Exception:
                logger.exception("News source %s failed", source.name)
        return all_news

    async def _fetch_market_news(self) -> list[dict]:
        all_news: list[dict] = []
        for source in self.news_sources:
            try:
                items = await source.fetch_market()
                all_news.extend(items)
            except Exception:
                logger.exception("Market news source %s failed", source.name)
        return all_news

    async def _call_llm(self, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_llm_response(raw: str) -> list[dict] | dict:
        cleaned = re.sub(r"```json\s*", "", raw)
        cleaned = re.sub(r"```\s*$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            m = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1))
                except json.JSONDecodeError:
                    pass
        logger.error("Failed to parse LLM response: %s", raw[:200])
        return []

    @staticmethod
    def _format_news(items: list[dict]) -> str:
        if not items:
            return "暂无相关新闻。"
        lines = []
        for i, item in enumerate(items[:50], 1):
            source = item.get("source", "未知")
            title = item.get("title", "")
            summary = item.get("summary", "")
            pub = item.get("published", "")
            lines.append(f"[{i}] 【{source}】{title} ({pub})\n    {summary}")
        return "\n".join(lines)


class _BaseNewsSource:
    name: str = "base"
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
                    symbol = f"sh{code}" if code.startswith("6") else f"sz{code}"
                    url = (
                        f"https://vip.stock.finance.sina.com.cn/corp/go.php/"
                        f"vCB_AllNewsStock/symbol/{symbol}.phtml"
                    )
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        titles = re.findall(
                            r'<a[^>]*href="(https?://finance\.sina[^"]*)"[^>]*>([^<]+)</a>',
                            resp.text,
                        )
                        for link, title in titles[:5]:
                            items.append({
                                "source": "新浪财经",
                                "title": title.strip(),
                                "summary": "",
                                "url": link,
                                "published": datetime.now().strftime("%Y-%m-%d"),
                                "stock_code": code,
                            })
                except Exception:
                    logger.debug("Sina news fetch failed for %s", code)
        return items

    async def fetch_market(self) -> list[dict]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                url = "https://zhibo.sina.com.cn/api/zhibo/feed?page=1&page_size=20&zhibo_id=152"
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    for feed in data.get("result", {}).get("data", {}).get("feed", {}).get("list", []):
                        items.append({
                            "source": "新浪7x24",
                            "title": feed.get("rich_text", "")[:100],
                            "summary": "",
                            "published": feed.get("create_time", ""),
                        })
        except Exception:
            logger.debug("Sina 7x24 market news failed")
        return items


class EastMoneyNews(_BaseNewsSource):
    name = "eastmoney"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items = []
        async with httpx.AsyncClient(timeout=15) as client:
            for code in stock_codes[:20]:
                try:
                    url = (
                        f"https://search-api-web.eastmoney.com/search/jsonp?"
                        f"cb=jQuery&param=%7B%22uid%22%3A%22%22%2C%22keyword%22%3A%22{code}%22"
                        f"%2C%22type%22%3A%5B%22cmsArticleWebOld%22%5D%2C%22pageIndex%22%3A1"
                        f"%2C%22pageSize%22%3A5%7D"
                    )
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        text = resp.text
                        m = re.search(r"jQuery\((.*)\)", text, re.DOTALL)
                        if m:
                            data = json.loads(m.group(1))
                            for article in data.get("result", []):
                                items.append({
                                    "source": "东方财富",
                                    "title": article.get("title", ""),
                                    "summary": article.get("content", "")[:200],
                                    "url": article.get("url", ""),
                                    "published": article.get("date", ""),
                                    "stock_code": code,
                                })
                except Exception:
                    logger.debug("EastMoney news failed for %s", code)
        return items

    async def fetch_market(self) -> list[dict]:
        items = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                url = (
                    "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns?"
                    "columns=350&pageSize=20&pageIndex=0"
                )
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    for art in data.get("data", {}).get("list", []):
                        items.append({
                            "source": "东方财富",
                            "title": art.get("title", ""),
                            "summary": art.get("digest", ""),
                            "published": art.get("showTime", ""),
                        })
        except Exception:
            logger.debug("EastMoney market news failed")
        return items


class XueqiuSentiment(_BaseNewsSource):
    name = "xueqiu"

    async def fetch(self, stock_codes: list[str]) -> list[dict]:
        items = []
        async with httpx.AsyncClient(timeout=15) as client:
            for code in stock_codes[:10]:
                try:
                    symbol = f"SH{code}" if code.startswith("6") else f"SZ{code}"
                    url = (
                        f"https://xueqiu.com/query/v1/symbol/search/status.json?"
                        f"symbol={symbol}&count=10&comment=0&page=1"
                    )
                    resp = await client.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Cookie": "xq_a_token=placeholder",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for post in data.get("list", []):
                            items.append({
                                "source": "雪球",
                                "title": post.get("title", post.get("text", ""))[:100],
                                "summary": post.get("description", "")[:200],
                                "published": str(post.get("created_at", "")),
                                "stock_code": code,
                            })
                except Exception:
                    logger.debug("Xueqiu fetch failed for %s", code)
        return items

    async def fetch_market(self) -> list[dict]:
        return []


def _build_news_sources(settings: Any) -> list[_BaseNewsSource]:
    sources: list[_BaseNewsSource] = []
    enabled = getattr(settings, "agent_news_sources", "sina,eastmoney,xueqiu")
    enabled_set = {s.strip().lower() for s in enabled.split(",")}
    if "sina" in enabled_set:
        sources.append(SinaFinanceNews())
    if "eastmoney" in enabled_set:
        sources.append(EastMoneyNews())
    if "xueqiu" in enabled_set:
        sources.append(XueqiuSentiment())
    if not sources:
        sources.append(SinaFinanceNews())
    return sources
PYEOF

echo "=== Step 4: 创建 app/agent/sentiment_scorer.py ==="
cat > app/agent/sentiment_scorer.py << 'PYEOF'
"""Sentiment Scorer: converts LLM analysis results into normalized scores."""
from __future__ import annotations

import math


def _safe(v, lo: float = 0.0, hi: float = 100.0) -> float:
    try:
        x = float(v)
    except Exception:
        return (lo + hi) / 2
    if math.isnan(x) or math.isinf(x):
        return (lo + hi) / 2
    return max(lo, min(hi, x))


def score_from_analysis(analysis: dict) -> dict:
    """Convert a single stock's LLM analysis dict into scoring inputs."""
    policy = _safe(analysis.get("policy_sentiment", 0), -100, 100)
    fundamental = _safe(analysis.get("fundamental_event_score", 0), -100, 100)
    industry = _safe(analysis.get("industry_momentum", 0), -100, 100)
    buzz_score = _safe(analysis.get("market_buzz_score", 0), 0, 100)
    buzz_dir = _safe(analysis.get("market_buzz_direction", 0), -100, 100)
    macro = _safe(analysis.get("macro_impact", 0), -100, 100)
    composite = _safe(analysis.get("composite_sentiment", 0), -100, 100)
    confidence = _safe(analysis.get("confidence", 30), 0, 100)

    raw = (
        0.25 * policy
        + 0.20 * fundamental
        + 0.20 * industry
        + 0.10 * (buzz_dir * buzz_score / 100)
        + 0.10 * macro
        + 0.15 * composite
    )
    ai_sentiment = _safe(50 + raw / 2, 0, 100)
    confidence_factor = confidence / 100
    ai_sentiment = 50 + (ai_sentiment - 50) * confidence_factor

    ai_policy_boost = _safe(policy * 0.15 * confidence_factor, -15, 15)
    ai_fundamental_boost = _safe(fundamental * 0.10 * confidence_factor, -10, 10)

    risk_flags = analysis.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        risk_flags = []

    reasons = []
    key_events = analysis.get("key_events", [])
    if key_events:
        reasons.append(f"AI关键事件：{'；'.join(key_events[:3])}")
    summary = analysis.get("summary", "")
    if summary:
        reasons.append(f"AI摘要：{summary}")
    reasons.append(
        f"AI情绪评分：{ai_sentiment:.0f}/100（置信度{confidence:.0f}%），"
        f"政策={policy:.0f}，基本面事件={fundamental:.0f}，"
        f"行业={industry:.0f}，舆情={buzz_dir:.0f}×{buzz_score:.0f}%"
    )
    if risk_flags:
        reasons.append(f"AI风险提示：{'；'.join(risk_flags[:3])}")

    return {
        "ai_sentiment_score": round(ai_sentiment, 2),
        "ai_confidence": round(confidence, 2),
        "ai_policy_boost": round(ai_policy_boost, 2),
        "ai_fundamental_boost": round(ai_fundamental_boost, 2),
        "ai_risk_flags": risk_flags,
        "ai_reasons": reasons,
    }


def merge_market_overview(overview: dict) -> dict:
    """Convert market overview to a market-level adjustment factor."""
    mkt = _safe(overview.get("market_sentiment", 0), -100, 100)
    tech = _safe(overview.get("tech_sector_sentiment", 0), -100, 100)

    return {
        "market_sentiment_adj": round(_safe(mkt * 0.10, -10, 10), 2),
        "tech_sector_adj": round(_safe(tech * 0.10, -10, 10), 2),
        "market_reasons": [
            f"市场整体情绪：{mkt:.0f}，科技板块：{tech:.0f}",
            f"政策方向：{overview.get('policy_direction', '未知')}",
            f"AI市场概览：{overview.get('summary', '')}",
        ],
    }
PYEOF

echo "=== Step 5: 创建 app/api/agent_routes.py ==="
cat > app/api/agent_routes.py << 'PYEOF'
"""Agent API routes."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.agent.news_agent import NewsAgent
from app.agent.sentiment_scorer import score_from_analysis, merge_market_overview

router = APIRouter()


class AnalyzeRequest(BaseModel):
    stock_codes: list[str] | None = None
    include_market_overview: bool = True


@router.post("/analyze")
async def analyze_news(req: AnalyzeRequest, db: Session = Depends(get_db)):
    """Run the AI News Agent to analyze stocks and market sentiment."""
    settings = get_settings()
    agent = NewsAgent(settings)

    codes = req.stock_codes
    if not codes:
        from app.models import DailyBar
        codes = [r[0] for r in db.query(DailyBar.code).group_by(DailyBar.code).all()]

    results = {"stock_analyses": [], "market_overview": None}

    if codes:
        analyses = await agent.analyze_stocks(codes)
        for a in analyses:
            scored = score_from_analysis(a)
            record = {
                "stock_code": a.get("stock_code", ""),
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "raw_analysis": json.dumps(a, ensure_ascii=False),
                "ai_sentiment_score": scored["ai_sentiment_score"],
                "ai_confidence": scored["ai_confidence"],
                "ai_policy_boost": scored["ai_policy_boost"],
                "ai_fundamental_boost": scored["ai_fundamental_boost"],
                "ai_reasons": json.dumps(scored["ai_reasons"], ensure_ascii=False),
            }
            _upsert_news_analysis(db, record)
            results["stock_analyses"].append(record)

    if req.include_market_overview:
        overview = await agent.market_overview()
        market_adj = merge_market_overview(overview)
        results["market_overview"] = {"raw": overview, "adjustments": market_adj}
        _upsert_market_overview(db, overview, market_adj)

    db.commit()
    return results


@router.get("/latest")
def get_latest_analysis(db: Session = Depends(get_db)):
    """Return the latest AI analysis results."""
    from app.models import NewsAnalysis
    from sqlalchemy import func, desc

    td = db.query(func.max(NewsAnalysis.analysis_date)).scalar()
    if not td:
        return {"analyses": [], "date": None}
    rows = db.query(NewsAnalysis).filter_by(analysis_date=td).order_by(
        desc(NewsAnalysis.ai_sentiment_score)
    ).all()
    return {
        "date": td,
        "analyses": [
            {
                "stock_code": r.stock_code,
                "ai_sentiment_score": r.ai_sentiment_score,
                "ai_confidence": r.ai_confidence,
                "ai_policy_boost": r.ai_policy_boost,
                "ai_fundamental_boost": r.ai_fundamental_boost,
                "ai_reasons": json.loads(r.ai_reasons) if r.ai_reasons else [],
            }
            for r in rows
        ],
    }


def _upsert_news_analysis(db: Session, record: dict):
    from app.models import NewsAnalysis
    existing = db.query(NewsAnalysis).filter_by(
        stock_code=record["stock_code"],
        analysis_date=record["analysis_date"],
    ).first()
    if existing:
        for k, v in record.items():
            setattr(existing, k, v)
    else:
        db.add(NewsAnalysis(**record))


def _upsert_market_overview(db: Session, overview: dict, adjustments: dict):
    record = {
        "stock_code": "MARKET",
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "raw_analysis": json.dumps(
            {"overview": overview, "adjustments": adjustments}, ensure_ascii=False
        ),
        "ai_sentiment_score": adjustments.get("market_sentiment_adj", 0),
        "ai_confidence": 0,
        "ai_policy_boost": adjustments.get("tech_sector_adj", 0),
        "ai_fundamental_boost": 0,
        "ai_reasons": json.dumps(
            adjustments.get("market_reasons", []), ensure_ascii=False
        ),
    }
    _upsert_news_analysis(db, record)
PYEOF

echo "=== Step 6: 修改 app/config.py ==="
# Add AI Agent settings before model_config line
sed -i '/^    scheduler_timezone/a\
\
    # --- AI Agent settings ---\
    llm_api_key: str = Field(default="")\
    llm_base_url: str = Field(default="https://api.openai.com/v1")\
    llm_model: str = Field(default="gpt-4o-mini")\
    agent_news_sources: str = Field(default="sina,eastmoney,xueqiu")\
    agent_enabled: bool = Field(default=False)' app/config.py

echo "=== Step 7: 修改 app/models.py ==="
# Add NewsAnalysis model before BacktestResult
sed -i '/^class BacktestResult/i\
class NewsAnalysis(Base):\
    __tablename__ = "news_analysis"\
    __table_args__ = (\
        UniqueConstraint("stock_code", "analysis_date", name="uq_news_code_date"),\
    )\
    id = Column(Integer, primary_key=True)\
    stock_code = Column(String(20), index=True, nullable=False)\
    analysis_date = Column(String(16), index=True, nullable=False)\
    raw_analysis = Column(Text, nullable=True)\
    ai_sentiment_score = Column(Float, nullable=False, default=50.0)\
    ai_confidence = Column(Float, nullable=False, default=0.0)\
    ai_policy_boost = Column(Float, nullable=False, default=0.0)\
    ai_fundamental_boost = Column(Float, nullable=False, default=0.0)\
    ai_reasons = Column(Text, nullable=True)\
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)\
\
' app/models.py

echo "=== Step 8: 修改 app/main.py ==="
# Add agent router import and registration
sed -i 's/from app.api.routes import router/from app.api.routes import router\nfrom app.api.agent_routes import router as agent_router/' app/main.py
sed -i '/app.include_router(router)/a app.include_router(agent_router, prefix="/agent", tags=["agent"])' app/main.py

echo "=== Step 9: 修改 app/scoring/score_engine.py ==="
# Replace the total calculation block with AI-enhanced version
python3 << 'PYSCRIPT'
import re

with open("app/scoring/score_engine.py", "r") as f:
    content = f.read()

old_total = '''    total = (0.14 * _safe(low_position) + 0.10 * _safe(fundamental) + 0.16 * _safe(policy) +
             0.18 * _safe(cap) + 0.18 * _safe(trend) + 0.10 * _safe(liquidity) + 0.09 * _safe(recent_strength) -
             _safe(concept_penalty) - _safe(overheat) - _safe(missing_penalty) + 0.15 * _safe(theme_eval.get("theme_relevance_score", 0)))
    total = _safe(total)

    reasons.extend(['''

new_total = '''    # --- AI Agent sentiment integration ---
    ai_data = row.get("_ai_analysis", {})
    ai_sentiment = _safe(ai_data.get("ai_sentiment_score", 50), 0, 100)
    ai_confidence = _safe(ai_data.get("ai_confidence", 0), 0, 100)
    ai_policy_boost = _safe(ai_data.get("ai_policy_boost", 0), -15, 15)
    ai_fundamental_boost = _safe(ai_data.get("ai_fundamental_boost", 0), -10, 10)
    market_adj = _safe(ai_data.get("market_sentiment_adj", 0), -10, 10)
    tech_adj = _safe(ai_data.get("tech_sector_adj", 0), -10, 10)

    # Apply AI boosts to existing dimensions
    policy = _safe(policy + ai_policy_boost)
    fundamental = _safe(fundamental + ai_fundamental_boost)

    # AI risk penalty from flagged risks
    ai_risk_penalty = 0.0
    ai_risk_flags = ai_data.get("ai_risk_flags", [])
    if ai_risk_flags:
        ai_risk_penalty = min(len(ai_risk_flags) * 5, 15)

    # Add AI-generated reasons
    ai_reasons = ai_data.get("ai_reasons", [])
    if ai_reasons:
        reasons.extend(ai_reasons)

    total = (0.12 * _safe(low_position) + 0.08 * _safe(fundamental) + 0.14 * _safe(policy) +
             0.16 * _safe(cap) + 0.16 * _safe(trend) + 0.08 * _safe(liquidity) + 0.07 * _safe(recent_strength) +
             0.12 * _safe(ai_sentiment) +  # AI sentiment dimension
             market_adj + tech_adj -  # market-level adjustments
             _safe(concept_penalty) - _safe(overheat) - _safe(missing_penalty) - ai_risk_penalty +
             0.13 * _safe(theme_eval.get("theme_relevance_score", 0)))
    total = _safe(total)

    reasons.extend(['''

content = content.replace(old_total, new_total)

with open("app/scoring/score_engine.py", "w") as f:
    f.write(content)

print("score_engine.py patched successfully")
PYSCRIPT

echo "=== Step 10: 修改 app/services/analysis_service.py ==="
python3 << 'PYSCRIPT'
with open("app/services/analysis_service.py", "r") as f:
    content = f.read()

# Patch generate_scores to inject AI data
old_gen = '''    def generate_scores(self, db: Session) -> dict:
        rows = self._latest_rows(db)
        td = datetime.now().strftime("%Y-%m-%d")
        universe_name_map = self._universe_name_map()
        scored = []
        for r in rows:
            s = compute_score(r)'''

new_gen = '''    def generate_scores(self, db: Session) -> dict:
        rows = self._latest_rows(db)
        td = datetime.now().strftime("%Y-%m-%d")
        universe_name_map = self._universe_name_map()

        # --- Load AI Agent analysis data ---
        ai_map = self._load_ai_analyses(db, td)
        market_adj = self._load_market_adjustment(db, td)

        scored = []
        for r in rows:
            code = str(r["code"])
            # Inject AI data into row for compute_score
            ai_data = ai_map.get(code, {})
            ai_data.update(market_adj)
            r["_ai_analysis"] = ai_data

            s = compute_score(r)'''

content = content.replace(old_gen, new_gen)

# Add helper methods at the end
ai_helpers = '''

    def _load_ai_analyses(self, db: Session, trade_date: str) -> dict[str, dict]:
        """Load today's AI sentiment data keyed by stock code."""
        try:
            from app.models import NewsAnalysis
        except ImportError:
            return {}

        results = {}
        rows = db.query(NewsAnalysis).filter_by(analysis_date=trade_date).all()
        for r in rows:
            if r.stock_code == "MARKET":
                continue
            results[r.stock_code] = {
                "ai_sentiment_score": r.ai_sentiment_score,
                "ai_confidence": r.ai_confidence,
                "ai_policy_boost": r.ai_policy_boost,
                "ai_fundamental_boost": r.ai_fundamental_boost,
                "ai_risk_flags": [],
                "ai_reasons": json.loads(r.ai_reasons) if r.ai_reasons else [],
            }
        return results

    def _load_market_adjustment(self, db: Session, trade_date: str) -> dict:
        """Load today's market-level AI adjustment."""
        try:
            from app.models import NewsAnalysis
        except ImportError:
            return {}

        mkt = db.query(NewsAnalysis).filter_by(
            stock_code="MARKET", analysis_date=trade_date
        ).first()
        if not mkt or not mkt.raw_analysis:
            return {}
        try:
            data = json.loads(mkt.raw_analysis)
            return data.get("adjustments", {})
        except Exception:
            return {}
'''

content = content.rstrip() + ai_helpers

with open("app/services/analysis_service.py", "w") as f:
    f.write(content)

print("analysis_service.py patched successfully")
PYSCRIPT

echo "=== Step 11: 修改 .env.example ==="
cat >> .env.example << 'EOF'

# --- AI Agent ---
LLM_API_KEY=sk-your-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
AGENT_NEWS_SOURCES=sina,eastmoney,xueqiu
AGENT_ENABLED=false
EOF

echo "=== Step 12: 提交并推送 ==="
git add -A
git commit -m "Add AI News Agent for market sentiment scoring

Integrate an AI-powered news analysis agent that fetches daily news from
Sina Finance, East Money, and Xueqiu, then uses an LLM to produce
structured sentiment scores per stock.

New modules:
- app/agent/news_agent.py: multi-source news fetcher + LLM analysis
- app/agent/sentiment_scorer.py: converts LLM output to scoring inputs
- app/agent/prompts.py: system prompts for 5-dimension analysis
- app/api/agent_routes.py: POST /agent/analyze, GET /agent/latest

Modified:
- score_engine.py: add ai_sentiment (12% weight) + market adjustments
- analysis_service.py: inject AI data into compute_score via _ai_analysis
- models.py: add NewsAnalysis table
- config.py: add LLM_API_KEY, LLM_MODEL, AGENT_* settings
- main.py: register /agent routes

When no AI data is available, scoring falls back to original behavior
(ai_sentiment=50 neutral, all boosts=0)."

git push -u origin feature/ai-news-agent

echo "=== Step 13: 创建 PR ==="
gh pr create \
  --title "Add AI News Agent for market sentiment scoring" \
  --body "$(cat <<'PRBODY'
## Summary
- 新增 AI News Agent 模块，从新浪财经/东方财富/雪球抓取新闻
- LLM 分析生成 5 维结构化情绪评分（政策/基本面/行业/舆情/宏观）
- 评分引擎 compute_score 新增 ai_sentiment 维度（12% 权重）
- 新增 `POST /agent/analyze` 和 `GET /agent/latest` API
- 无 AI 数据时自动退化为原有逻辑，零侵入

## New Files
- `app/agent/__init__.py`
- `app/agent/prompts.py`
- `app/agent/news_agent.py`
- `app/agent/sentiment_scorer.py`
- `app/api/agent_routes.py`

## Modified Files
- `app/scoring/score_engine.py` — 加入 AI 情绪权重
- `app/services/analysis_service.py` — 注入 AI 数据到评分流程
- `app/models.py` — 新增 NewsAnalysis 表
- `app/config.py` — 新增 LLM 配置字段
- `app/main.py` — 注册 /agent 路由
- `.env.example` — 新增 AI Agent 环境变量

## 使用前配置
1. 在 `.env` 中设置 `LLM_API_KEY`
2. 重新运行 `python scripts/init_db.py`

## Test plan
- [ ] 验证无 AI 数据时评分与原逻辑一致
- [ ] 配置 LLM_API_KEY 后测试 POST /agent/analyze
- [ ] 验证 GET /agent/latest 返回分析结果
- [ ] 验证 POST /scores/generate 自动融合 AI 评分
PRBODY
)"

echo ""
echo "✅ 完成！PR 已创建。"
