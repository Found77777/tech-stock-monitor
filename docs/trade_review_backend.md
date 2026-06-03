# 交易日志与每日复盘后端模块

## 新增文件列表

- `app/review/__init__.py`
- `app/review/schemas.py`
- `app/review/service.py`
- `app/review/routes.py`
- `scripts/migrate_review_tables.py`
- `tests/test_review_module.py`

同时扩展：

- `app/models.py`：新增 `TradePlan`、`DailyReview`、`TradeLog`。
- `app/main.py`：注册 `/api/review/*` 路由。
- `app/scheduler/jobs.py`：新增 15:30 自动创建 pending 复盘草稿任务。

## 数据库 ER 图说明

```text
trade_plan (1 row per trade_date)
  trade_date ─────┐
                  │ logical date join
trade_log (*)     │
  trade_date ─────┤
  symbol          │
                  │
daily_review (1 row per review_date)
  review_date ────┘
```

- `trade_plan.trade_date` 唯一，对应盘前交易计划。
- `daily_review.review_date` 唯一，对应盘后复盘；scheduler 会在 15:30 自动补 `status=pending` 草稿。
- `trade_log.trade_date` 可对应多条交易执行记录。
- 三张表通过日期做逻辑关联，不影响现有 `stock_scores`、`enhanced_stock_scores`、AI News Alpha 或资金流验证表。

## 新增 API 文档

### Trade Plan

#### `POST /api/review/trade-plan`
创建或更新盘前计划。

#### `GET /api/review/trade-plan/{trade_date}`
读取指定日期盘前计划。

### Daily Review

#### `POST /api/review/daily`
创建或更新盘后复盘。

#### `GET /api/review/daily/{review_date}`
读取指定日期盘后复盘。

### Trade Log

#### `POST /api/review/trades`
新增一条实际交易记录。

#### `GET /api/review/trades/{trade_date}`
读取指定日期交易日志。

### AI Review Summary

#### `POST /api/review/ai-summary`
基于 daily review、trade plan、trade logs 生成结构化复盘总结：

```json
{
  "strengths": [],
  "weaknesses": [],
  "repeated_mistakes": [],
  "discipline_score": 0,
  "risk_score": 0,
  "suggestions": []
}
```

### Plan Drift

#### `GET /api/review/plan-drift?trade_date=YYYY-MM-DD`
比较盘前计划与实际执行，识别计划外交易、未按计划交易、超仓、追高/情绪交易。

### Stats

#### `GET /api/review/stats?days=30`
返回最近 N 天胜率、平均收益、最大回撤、平均纪律分、连续盈利/亏损天数。

## curl 测试示例

```bash
curl -X POST http://127.0.0.1:8000/api/review/trade-plan \
  -H 'Content-Type: application/json' \
  -d '{
    "trade_date":"2026-06-02",
    "watch_symbols":["002465"],
    "focus_sectors":["通信"],
    "market_view":"震荡偏强",
    "bull_case":"科技资金回流",
    "bear_case":"缩量回落",
    "max_position":10000,
    "planned_trades":[{"symbol":"002465","action":"buy"}],
    "risk_notes":["不追高"]
  }'

curl -X POST http://127.0.0.1:8000/api/review/trades \
  -H 'Content-Type: application/json' \
  -d '{
    "trade_date":"2026-06-02",
    "symbol":"600850",
    "action":"buy",
    "quantity":1000,
    "entry_price":12.0,
    "exit_price":11.8,
    "pnl":-200,
    "planned_trade":false,
    "actual_reason":"情绪追高",
    "result_score":40,
    "notes":"计划外"
  }'

curl 'http://127.0.0.1:8000/api/review/plan-drift?trade_date=2026-06-02'

curl -X POST http://127.0.0.1:8000/api/review/ai-summary \
  -H 'Content-Type: application/json' \
  -d '{"review_date":"2026-06-02"}'

curl 'http://127.0.0.1:8000/api/review/stats?days=30'
```
