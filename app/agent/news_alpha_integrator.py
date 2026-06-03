"""
统一的新闻 alpha 集成模块
确保 Agent 输出正确流入评分系统，避免数据源不一致
"""
from __future__ import annotations

import json
import logging
from sqlalchemy.orm import Session

from app.agent.news_alpha_engine import compute_news_alpha
from app.models import NewsAlphaSignal

logger = logging.getLogger(__name__)


def integrate_news_alpha_to_analysis(
    db: Session,
    code: str,
    trade_date: str,
    news_items: list[dict],
    stock_meta: dict,
) -> dict[str, float]:
    """
    计算新闻 alpha 并提取评分所需的关键字段
    
    Args:
        db: 数据库会��
        code: 股票代码
        trade_date: 交易日期 (YYYY-MM-DD)
        news_items: 新闻列表
        stock_meta: 股票元数据 {"code": str, "name": str}
    
    Returns:
        {
            "ai_sentiment_score": float,      # 0-100 情绪分数
            "ai_confidence": float,            # 0-1 置信度
            "ai_policy_boost": float,          # -15到+15 政策加持
            "ai_fundamental_boost": float,    # -10到+10 基本面加持
            "ai_risk_flags": list[str],       # 风险标记
            "ai_reasons": list[str],          # 分析原因
            "raw_alpha": dict                 # 原始 alpha 结果（用于审计）
        }
    """
    # 计算新闻 alpha
    alpha_result = compute_news_alpha(news_items, stock_meta)
    
    # 分离出评分系统需要的字段
    ai_data = {
        "ai_sentiment_score": _map_alpha_to_sentiment(alpha_result),
        "ai_confidence": alpha_result.get("confidence", 0.0),
        "ai_policy_boost": _extract_policy_boost(alpha_result),
        "ai_fundamental_boost": _extract_fundamental_boost(alpha_result),
        "ai_risk_flags": alpha_result.get("risk_flags", []),
        "ai_reasons": alpha_result.get("risk_flags", []),
        "raw_alpha": alpha_result,
    }
    
    # 同时持久化详细事件到 NewsAlphaSignal（用于审计/分析）
    _persist_alpha_events(db, code, trade_date, alpha_result)
    
    logger.info(
        "integrate_news_alpha code=%s trade_date=%s sentiment=%.0f confidence=%.2f policy_boost=%.1f fundamental_boost=%.1f",
        code,
        trade_date,
        ai_data["ai_sentiment_score"],
        ai_data["ai_confidence"],
        ai_data["ai_policy_boost"],
        ai_data["ai_fundamental_boost"],
    )
    
    return ai_data


def _map_alpha_to_sentiment(alpha_result: dict) -> float:
    """
    将新闻 alpha 调整结果映射到 0-100 的情绪分数
    
    规则：
    - alpha_adjustment > 0 且置信度高 → 看涨（60-100）
    - alpha_adjustment < 0 且置信度高 → 看跌（0-40）
    - alpha_adjustment ≈ 0 或无新闻 → 中性（50）
    
    Args:
        alpha_result: compute_news_alpha 的返回结果
    
    Returns:
        情绪分数 0-100
    """
    adj = alpha_result.get("news_alpha_adjustment", 0.0)
    confidence = alpha_result.get("confidence", 0.0)
    
    # 基础分数：中性为 50
    base = 50.0
    
    # 根据 alpha 调整幅度和���信度调整情绪
    if adj > 0:
        # 正向：调整幅度越大、置信度越高 → 越看涨
        boost = min(30, abs(adj) * 5) * (0.5 + confidence * 0.5)
        return min(100.0, base + boost)
    elif adj < 0:
        # 负向：调整幅度越大、置信度越高 → 越看跌
        markdown = min(30, abs(adj) * 5) * (0.5 + confidence * 0.5)
        return max(0.0, base - markdown)
    else:
        # 无新闻或无有效alpha → 中性
        return 50.0


def _extract_policy_boost(alpha_result: dict) -> float:
    """
    从新闻事件中提取政策相关调整
    
    优先级：policy_catalyst > industry_catalyst > 其他
    """
    events = alpha_result.get("top_news_events", [])
    
    policy_events = [
        e for e in events
        if e.get("event_type") == "policy_catalyst"
    ]
    industry_events = [
        e for e in events
        if e.get("event_type") == "industry_catalyst"
    ]
    
    # 政策事件权重更高
    policy_boost = sum(
        e.get("single_news_alpha", 0) * 2.5
        for e in policy_events
    )
    
    industry_boost = sum(
        e.get("single_news_alpha", 0) * 1.5
        for e in industry_events
    )
    
    total_boost = policy_boost + industry_boost
    
    return max(-15.0, min(15.0, total_boost))


def _extract_fundamental_boost(alpha_result: dict) -> float:
    """
    从新闻事件中提取基本面相关调整
    
    包括：earnings, company_order, product_tech, capacity_expansion, financing
    """
    events = alpha_result.get("top_news_events", [])
    fundamental_event_types = {
        "earnings",
        "company_order",
        "product_tech",
        "capacity_expansion",
        "financing",
    }
    
    fundamental_events = [
        e for e in events
        if e.get("event_type") in fundamental_event_types
    ]
    
    if not fundamental_events:
        return 0.0
    
    total_boost = sum(
        e.get("single_news_alpha", 0)
        for e in fundamental_events
    )
    
    return max(-10.0, min(10.0, total_boost))


def _persist_alpha_events(
    db: Session,
    code: str,
    trade_date: str,
    alpha_result: dict
) -> None:
    """
    保存详细的新闻事件到 NewsAlphaSignal 表（用于审计）
    
    这与评分无关，只是为了追踪 Agent 的决策过程
    """
    # 删除旧数据
    db.query(NewsAlphaSignal).filter_by(
        stock_code=code,
        analysis_date=trade_date
    ).delete()
    
    # 插入新事件
    for ev in alpha_result.get("top_news_events", []):
        try:
            db.add(NewsAlphaSignal(
                stock_code=code,
                analysis_date=trade_date,
                news_title=str(ev.get("title", ""))[:500],
                news_url="",
                source="",
                publish_time="",
                event_type=str(ev.get("event_type", "unknown")),
                impact_direction=str(ev.get("impact_direction", "neutral")),
                impact_horizon=str(ev.get("impact_horizon", "short_term")),
                relevance_score=float(ev.get("news_relevance_score", 0)),
                importance_score=float(ev.get("news_importance_score", 0)),
                freshness_score=float(ev.get("news_freshness_score", 0)),
                confidence=float(ev.get("confidence", 0)),
                single_news_alpha=float(ev.get("single_news_alpha", 0)),
                alpha_reasons=json.dumps(
                    ev.get("alpha_reasons", []),
                    ensure_ascii=False
                ),
            ))
        except Exception as e:
            logger.exception(
                "Failed to persist alpha event code=%s title=%s error=%s",
                code,
                ev.get("title", ""),
                e,
            )
