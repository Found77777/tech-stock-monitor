"""
改进建议文档 - 还需要修改的地方

本文档列出了改进 PR 后，后续应该进行的 refinement。
"""

# ========================================
# 🔴 第一优先级 - 必须改
# ========================================

## 问题1: agent_routes.py 没有用改进的新闻源
位置: app/api/agent_routes.py 第 16 行

当前:
```python
from app.agent.news_agent import NewsAgent
```

应改为:
```python
from app.agent.news_agent import NewsAgent
from app.agent.news_sources_improved import build_improved_news_sources
from app.agent.news_alpha_integrator import integrate_news_alpha_to_analysis
```

然后在 analyze_top 函数中使用改进的集成:
```python
@router.post("/analyze-top")
async def analyze_top(req: AnalyzeTopRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    
    # ✅ 使用改进的新闻源而不是旧的 NewsAgent
    for idx, s in enumerate(base_rows, start=1):
        code = _norm_code(s.code)
        
        # 使用改进的新闻源获取新闻
        news_sources = build_improved_news_sources(settings)
        news_items = []
        for source in news_sources:
            news_items.extend(await source.fetch([code]))
        
        # 使用统一的集成函数
        ai_data = integrate_news_alpha_to_analysis(
            db=db,
            code=code,
            trade_date=trade_date,
            news_items=news_items,
            stock_meta={"code": code, "name": s.name or ""}
        )
```

---

## 问题2: NewsAgent 的 _fetch_market_news 容易崩溃
位置: app/agent/news_agent.py 第 168-176 行

当前只有 try-except，但没有日志记录失败的源

改进:
```python
async def _fetch_market_news(self) -> list[dict]:
    all_news: list[dict] = []
    failed_sources = []
    
    for source in self.news_sources:
        try:
            news = await source.fetch_market()
            logger.info(f"Market news source {source.name}: got {len(news or [])} items")
            all_news.extend(news or [])
        except Exception as e:
            failed_sources.append(f"{source.name}: {str(e)}")
            logger.exception(f"Market news source {source.name} failed")
    
    if failed_sources:
        logger.warning(f"Some market news sources failed: {failed_sources}")
    
    return _dedup_news(_normalize_news_items(all_news))
```

---

## 问题3: LLM 分析失败时的兜底不够好
位置: app/api/agent_routes.py 第 113-121 行

当前: LLM 失败就返回空结果

改进: 应该返回更有意义的默认值
```python
if not a:
    is_fallback = True
    a = {
        "stock_code": code,
        "policy_sentiment": 25,  # ← 改为默认中性 (25-75 范围内)
        "fundamental_event_score": 30,
        "industry_momentum": 40,
        "market_buzz_score": 35,
        "market_buzz_direction": 0,
        "macro_impact": 20,
        "composite_sentiment": 40,  # ← 中性
        "confidence": 0.1,  # ← 低置信度
        "risk_flags": ["LLM分析失败，使用默认中性值"],
        "key_events": [],
        "summary": "LLM分析失败，使用规则引擎",
    }
```

---

# ========================================
# 🟡 第二优先级 - 应该改
# ========================================

## 问题4: 缺少 Agent 健康检查接口
位置: 应该在 agent_routes.py 中添加

新增:
```python
@router.get("/health")
def agent_health(db: Session = Depends(get_db)):
    """检查 Agent 系统的健康状态"""
    settings = get_settings()
    
    health_status = {
        "agent_enabled": settings.agent_enabled,
        "agent_debug_mode": settings.agent_debug_mode,
        "news_sources": settings.agent_news_sources.split(","),
        "llm_configured": bool(settings.llm_api_key),
        "tushare_configured": bool(settings.tushare_token),
        "last_analysis_date": None,
        "last_error": None,
    }
    
    # 检查最近的分析
    try:
        from app.models import NewsAnalysis
        last = db.query(NewsAnalysis.analysis_date).order_by(
            NewsAnalysis.analysis_date.desc()
        ).first()
        if last:
            health_status["last_analysis_date"] = last[0]
    except Exception as e:
        health_status["last_error"] = str(e)
    
    return health_status
```

---

## 问题5: 没有 Agent 配置验证函数
位置: 应该在 app/agent/config_validator.py 中新增

新增文件:
```python
"""验证 Agent 配置的合法性"""
from app.config import Settings

def validate_agent_config(settings: Settings) -> tuple[bool, list[str]]:
    """
    验证 Agent 配置
    
    返回: (是否有效, 警告列表)
    """
    warnings = []
    
    if not settings.agent_enabled:
        warnings.append("Agent 被禁用 (AGENT_ENABLED=false)")
    
    if settings.agent_enabled and not settings.llm_api_key:
        warnings.append("Agent 启用但 LLM_API_KEY 未配置")
    
    sources = {s.strip() for s in settings.agent_news_sources.split(",")}
    
    if "tushare" in sources and not settings.tushare_token:
        warnings.append("Tushare 新闻源被选中但 TUSHARE_TOKEN 未配置")
    
    if not sources:
        warnings.append("没有配置任何新闻源")
    
    # 检查是否有有效的新闻源
    valid_sources = {"tushare", "akshare", "sina", "eastmoney", "xueqiu"}
    invalid = sources - valid_sources
    if invalid:
        warnings.append(f"未知的新闻源: {invalid}")
    
    return len(warnings) == 0, warnings
```

---

## 问题6: 缺少 Agent 性能监控
位置: 应该在 app/agent/metrics.py 中新增

新增文件:
```python
"""Agent 性能指标收集"""
from datetime import datetime
from typing import Any

class AgentMetrics:
    """收集 Agent 的运行指标"""
    
    def __init__(self):
        self.news_fetch_success_count = 0
        self.news_fetch_failed_count = 0
        self.llm_call_count = 0
        self.llm_error_count = 0
        self.alpha_adjustments = []  # 历史调整值
        self.last_run_time = None
        self.average_processing_time = 0.0
    
    def record_news_fetch(self, success: bool):
        if success:
            self.news_fetch_success_count += 1
        else:
            self.news_fetch_failed_count += 1
    
    def record_llm_call(self, success: bool):
        self.llm_call_count += 1
        if not success:
            self.llm_error_count += 1
    
    def record_alpha_adjustment(self, value: float):
        self.alpha_adjustments.append({
            "value": value,
            "timestamp": datetime.now(),
        })
    
    def get_success_rate(self) -> float:
        total = self.news_fetch_success_count + self.news_fetch_failed_count
        if total == 0:
            return 0.0
        return self.news_fetch_success_count / total
    
    def get_summary(self) -> dict[str, Any]:
        return {
            "news_fetch_success": self.news_fetch_success_count,
            "news_fetch_failed": self.news_fetch_failed_count,
            "fetch_success_rate": f"{self.get_success_rate():.2%}",
            "llm_calls": self.llm_call_count,
            "llm_errors": self.llm_error_count,
            "avg_processing_time": f"{self.average_processing_time:.2f}s",
        }

# 全局指标实例
agent_metrics = AgentMetrics()
```

---

# ========================================
# 🟢 第三优先级 - 可选改进
# ========================================

## 问题7: 没有 Agent 配置文档
应该在 docs/ 目录下新增:

- docs/agent-configuration.md: Agent 配置指南
- docs/agent-troubleshooting.md: 常见问题排查
- docs/agent-api-reference.md: API 文档

---

## 问题8: 没有 Agent 单元测试
应该在 tests/ 目录下新增:

- tests/test_news_alpha_integrator.py
- tests/test_news_sources_improved.py
- tests/test_agent_routes.py

---

# ========================================
# 改进优先级总结
# ========================================

优先级顺序:
1. ✅ 问题1: agent_routes.py 集成改进新闻源 (必须)
2. ✅ 问题2: NewsAgent 错误处理 (必须)
3. ✅ 问题3: LLM 兜底逻辑 (必须)
4. 🟡 问题4: 健康检查接口 (建议)
5. 🟡 问题5: 配置验证 (建议)
6. 🟡 问题6: 性能监控 (建议)
7. 🟢 问题7: 文档 (可选)
8. 🟢 问题8: 单元测试 (可选)

建议:
- 先做完第 1-3 项 (合并到当前 PR 中)
- 然后做第 4-6 项 (单独 PR)
- 文档和测试可以后续跟进
"""