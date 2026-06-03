# A股科技标的实时监控平台

## Phase 4：回测与因子有效性验证

### 运行
```bash
pip install -r requirements.txt
python scripts/init_db.py
pytest -q
uvicorn app.main:app --reload
streamlit run dashboard/streamlit_app.py
```

### 新增能力
- 因子IC检验：`POST /backtest/factor-ic`
- 分组收益检验：`POST /backtest/factor-groups`
- 信号事件研究：`POST /backtest/signals`
- Top Score组合回测：`POST /backtest/top-score`
- 最新回测结果：`GET /backtest/results/latest`

### 术语说明
- IC：因子值与未来收益横截面相关性（Pearson/Spearman）
- 分组收益：按因子分位分组，比较各组未来收益与Top-Bottom spread
- 事件研究：按信号触发日统计后续收益、胜率、样本数

### 当前局限性
- 未处理复权
- 未处理真实交易成本
- 未处理涨跌停
- 未处理停牌
- benchmark 暂为 mock
- 股票池过滤仍是粗筛

### Codex 容器提示
在部分代理网络环境下，AKShare 上游接口可能被阻断。
可在 `.env` 中设置 `USE_MOCK_DATA=true`，用于验证完整系统链路（refresh/history/signals/scores/watchlist）。

### 使用新浪实时数据源
在 `.env` 中设置：

```
REAL_DATA_SOURCE=sina
USE_MOCK_DATA=false
```

说明：AKShare 的 `stock_zh_a_spot_em` 底层依赖东方财富，某些代理网络会被阻断。
此时可切换到新浪实时接口（非东方财富）进行本地稳定验证。

### 使用 pytdx 实时数据源
在 `.env` 中设置：

```
REAL_DATA_SOURCE=pytdx
USE_MOCK_DATA=false
```

说明：pytdx 通过行情网关协议拉取，不依赖网页 requests 抓取方式，适合在网页风控场景下进行真实行情验证。

### 主板科技股票池（人工维护）
当前使用 `data/tech_universe_mainboard.csv` 作为第一版主板科技股票池来源（人工维护）。
- 仅保留主板代码：600/601/603/605/000/001/002
- 排除创业板/科创板/北交所与 ST
- 科技方向通过 `sector/theme` 字段维护

后续可升级为申万行业/中证行业/概念板块自动更新。


### 代理配置建议
不再建议在 Terminal 全局 `export HTTP_PROXY/HTTPS_PROXY`。

请在 `.env` 中配置 DeepSeek 与 LLM 代理：

```
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_HTTP_PROXY=http://127.0.0.1:7890
```

说明：
- Agent 默认使用 DeepSeek OpenAI-compatible Chat Completions：`LLM_BASE_URL=https://api.deepseek.com`，`LLM_MODEL=deepseek-chat`。
- DeepSeek 调用只使用 `LLM_HTTP_PROXY`，不依赖系统全局 HTTP_PROXY/HTTPS_PROXY。
- AKShare/EastMoney/Sina 行情直连（不走该代理）。

### AI Agent 运维检查
- `GET /agent/health`：查看 Agent 可用状态、启用的新闻源、LLM/代理配置状态与配置告警。
- `GET /agent/config/validate`：仅校验 Agent 配置，不访问外部网络；适合启动前排查 `.env`。
- 当 LLM 调用失败或 JSON 解析失败时，系统不会清空已抓取新闻，会退化到规则引擎生成个股/市场分析，并在响应中保留 `llm_status` / `llm_parse_status` 等调试信息。
- 默认新闻源为 `sina,eastmoney,cninfo,baidu,rss`，用于避免单一来源失败导致 Agent 无新闻可用。

## Web 前端 MVP（Next.js）

前端位于 `frontend/`，使用 Next.js App Router、TypeScript、Tailwind CSS、shadcn/ui 风格组件和 Recharts。

### 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认 API 地址为 `http://127.0.0.1:8000`。如需覆盖：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

### 前端路由结构

- `/`：Dashboard，一键运行 market refresh、history refresh、signals、scores、capital-flow verification、AI analyze-top，并展示 Top/Enhanced Watchlist。
- `/enhanced-watchlist`：Enhanced Watchlist，展示资金流来源、AI News Alpha 调整、增强分和新闻事件摘要。
- `/daily-review`：每日复盘表单，支持读取 pending draft 并创建/更新复盘。
- `/trade-plan`：盘前交易计划。
- `/trade-log`：实际交易日志录入与当日日志查看。
- `/plan-drift`：计划 vs 执行偏差分析。
- `/review-stats`：最近 30 天复盘统计与 Recharts 图表。
- `/ai-review-summary`：结构化 AI 复盘总结。

后端已允许 CORS 来源：`http://localhost:3000`、`http://localhost:5173`。

## 推荐数据源与资金流语义

推荐真实行情源：

```bash
USE_MOCK_DATA=false
REAL_DATA_SOURCE=sina
HISTORY_DATA_SOURCE=sina
ENABLE_DATA_SOURCE_FALLBACK=true
```

`REAL_DATA_SOURCE` 支持：`efinance`、`sina`、`akshare`、`mock`。当前推荐实时行情使用 `sina`，历史K线也使用新浪高级日线接口；AKShare/EastMoney/efinance 行情在批量历史请求下可能不稳定。开启 fallback 后，行情源按 `sina -> mock`、`efinance -> sina -> mock` 或 `akshare -> efinance -> sina -> mock` 降级，并在接口返回 `data_source_used`。

推荐配置：Sina 用于实时行情快照与新浪高级日线历史K线；历史K线的成交额由 OHLC 均价 × 成交股数估算，换手率只有在有可靠流通股本时才计算，否则显示 N/A；efinance `get_history_bill` 仅用于历史资金流。

资金流配置默认不允许 proxy 静默伪装成真实资金流：

```bash
CAPITAL_FLOW_SOURCE=efinance
CAPITAL_FLOW_ALLOW_PROXY=false
CAPITAL_FLOW_RETRY=3
CAPITAL_FLOW_SLEEP_MIN=10.0
CAPITAL_FLOW_SLEEP_MAX=20.0
CAPITAL_FLOW_CACHE_ENABLED=true
```

资金流状态说明：

- `efinance_history_bill`：真实 efinance `get_history_bill` 历史资金流，`capital_flow_confidence` 会按来源置信度和数据完整度动态计算，推荐用于资金流验证。
- `real_eastmoney`：真实 EastMoney/AKShare 单股资金流，`capital_flow_is_real=true`。
- `proxy_estimated`：量价估算资金流，不是真实主力资金流；仅当显式 `CAPITAL_FLOW_SOURCE=proxy` 时使用，最多影响 ±2 分。
- `unavailable`：真实资金流不可用，未使用 proxy 估算，`capital_flow_adjustment=0`。
- `none`：不启用资金流，`capital_flow_adjustment=0`。

显式启用 proxy 估算：

```bash
CAPITAL_FLOW_SOURCE=proxy
# proxy_estimated 不是推荐默认值；仅在明确接受量价估算时启用
```

验证命令：

```bash
curl -X POST http://127.0.0.1:8000/market/refresh
curl -X POST "http://127.0.0.1:8000/history/refresh?days=120"
curl -X POST http://127.0.0.1:8000/signals/generate
curl -X POST http://127.0.0.1:8000/scores/generate
curl "http://127.0.0.1:8000/watchlist/enhanced-top?limit=10"
```
