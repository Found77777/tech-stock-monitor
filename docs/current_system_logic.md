# tech-stock-monitor 当前系统逻辑说明（Current System Logic）

> 更新时间：2026-05-26  
> 定位：**研究与监控系统**，不是自动交易系统。

---

## 1. 项目目标

### 1.1 当前系统要解决的问题
`tech-stock-monitor` 旨在解决一个实际研究问题：

- 在 A 股主板科技股范围内，建立一套可持续运行的“行情拉取 → 历史落库 → 因子计算 → 信号生成 → 评分排序 → 可视化”流程；
- 用规则引擎识别“**低位结构改善 + 资金量价改善 + 主题相关性较高**”的候选标的；
- 将结果以 API + Dashboard 方式输出，便于日常复盘与跟踪。

### 1.2 “主板科技低位转强监控器”的定义
当前定义是一个**结构化监控框架**，而非单指标选股器：

- “低位”不是简单“跌得多”，而是结合 250 日位置、横盘、均线结构；
- “转强”不是单日涨停，而是量价共振、趋势修复、结构改善的组合信号；
- “科技相关性”不仅看静态标签，还逐步引入主题相关性规则评分（Theme Research Engine v1）。

### 1.3 明确边界
当前系统**不是**：

- 自动交易执行系统；
- 价格预测模型；
- 投资建议系统。

当前系统**是**：

- 研究与监控基础设施；
- 因子/信号/评分试验平台；
- 可复盘的数据与可视化工具。

---

## 2. 当前整体架构

系统为典型分层架构：

1. **FastAPI 后端**：统一提供刷新、查询、生成信号/评分、回测接口。  
2. **Streamlit Dashboard**：操作入口和可视化看板。  
3. **SQLite 数据库**：本地持久化（后续可迁移 PostgreSQL）。  
4. **数据源层**：`sina / pytdx / akshare / mock` 可切换。  
5. **股票池层**：主板科技股票池（CSV + 规则过滤）。  
6. **历史 K 线层**：按 source 拉日线并入库 `daily_bars`。  
7. **因子层**：技术因子、流动性、相对强弱、低位结构、量价结构等。  
8. **信号层**：规则化 bullish/bearish/warning 事件。  
9. **评分层**：多维加权 + 惩罚项，输出 watchlist 排序。  
10. **回测层**：IC、分组、事件研究、TopN 组合回测。

---

## 3. 当前数据流（按操作顺序）

### 3.1 `POST /market/refresh`
- 读取配置，选择真实或 mock 数据源；
- 拉取实时行情（批量）；
- 主板科技池过滤（代码规则 + 股票池）；
- 应用流动性约束（如最小成交额）；
- 写入 `stock_snapshots`（去重约束：`code + timestamp`）。

### 3.2 `POST /history/refresh?days=120`
- 根据 `REAL_DATA_SOURCE` 选择历史数据源；
- 对当前跟踪标的批量拉日线；
- 字段标准化并补齐 `name`（snapshot → universe → code fallback）；
- 写入 `daily_bars`（去重约束：`code + trade_date`）。

### 3.3 `POST /signals/generate`
- 从 `daily_bars` 计算最新因子快照；
- 调用信号引擎生成可解释信号；
- 写入 `stock_signals`（按 `code + trade_date + signal_name` 去重）。

### 3.4 `POST /scores/generate`
- 从 `daily_bars` 计算最新因子；
- 评分引擎计算 `total_score` 与子分；
- `AnalysisService` 做写库安全防护（NaN/inf/None）；
- 写入 `stock_scores`（按 `code + trade_date` 去重）。

### 3.5 `GET /watchlist/top?limit=N`
- 查询最新交易日 `stock_scores`；
- 按 `total_score` 降序；
- 返回前 N 个观察标的。

### 3.6 Dashboard 展示
- 调用 API 获取 snapshot/signals/scores/watchlist 等；
- 通过 `normalize_records` 统一兼容 list/dict payload；
- 展示主表、筛选器、详情、辅助表格与错误信息。

---

## 4. 数据源逻辑

### 4.1 关键开关
- `USE_MOCK_DATA=true/false`
- `REAL_DATA_SOURCE=sina|akshare|pytdx`

优先规则：
1. 若 `USE_MOCK_DATA=true`，使用 MockDataSource；
2. 否则使用 `REAL_DATA_SOURCE` 指定真实源。

### 4.2 Sina 实时行情
- 使用 `requests` 直连新浪接口，支持批量分组请求；
- 做字段解析与标准化（code/name/price/amount...）；
- 对缺失字段使用 None/0 并做后续安全处理。

### 4.3 Sina/Tencent 历史日线
- `HistoryDataService` 会按 source 选择对应历史接口；
- 已避免“默认强制走 AKShare EastMoney 历史接口”；
- 对返回嵌套结构做扁平化防御，避免 `float(dict)` 类错误。

### 4.4 为什么当前默认不依赖 AKShare/EastMoney
在受限网络或代理环境中，`push2his.eastmoney.com` 容易被拦截（403/ProxyError）。
因此工程上采用多源可切换并优先保证可运行性。

---

## 5. 股票池逻辑

### 5.1 股票池来源
- 主文件：`data/tech_universe_mainboard.csv`
- 功能：作为当前研究 universe 的显式维护源。

### 5.2 主板过滤规则
仅保留：
- 上交所：`600/601/603/605`
- 深交所：`000/001/002`

排除：
- 创业板：`300/301`
- 科创板：`688`
- 北交所：`8/4` 开头
- `ST/*ST`

### 5.3 当前字段
`code, name, sector, theme, fundamental_quality, policy_theme, concept_purity`

---

## 6. 当前评分逻辑（compute_score）

当前评分是“低位结构 + 主题相关 + 资金量价 + 风险惩罚”的组合。

主要分量：

- `low_position_score`（映射到 DB 的 `position_score`）
  - 综合 250 日回撤、250 日分位、横盘天数、MA 结构、120 日结构风险。
- `fundamental_score`
  - 目前是规则映射（strong/medium/weak）。
- `policy_alignment_score`
  - 当前由 Theme Engine 计算（并兼容旧字段 fallback）。
- `capital_inflow_score`
  - 当前在 DB 兼容字段中映射到 `momentum_score`。
- `trend_reversal_score`
  - 有因子则优先使用，否则 fallback 规则。
- `liquidity_score`
  - 由流动性因子模块给出。
- `concept_hype_penalty + overheat_penalty`
  - 合并映射到 DB 的 `risk_penalty`。

总分为加权与惩罚组合，输出 `total_score` 并做 0-100 安全截断。

### 6.1 与旧数据库字段映射（兼容）
由于 `stock_scores` 表结构未变，保持映射：

- `trend_score` ← trend reversal 相关
- `momentum_score` ← capital flow 相关
- `relative_strength_score` ← policy/theme alignment 相关
- `liquidity_score` ← liquidity
- `position_score` ← low position
- `risk_penalty` ← concept + overheat penalty

---

## 7. 当前 reasons 解释逻辑

`reasons` 以中文可读文本输出，覆盖：

- 低位状态（250 日回撤/分位/横盘/MA结构）
- 基本面标签说明
- 政策/主题匹配说明
- 概念纯度与对应惩罚
- 资金/量能与量价共振说明
- 过热/风险提示

目标是“可追踪、可复盘、可解释”。

---

## 8. 当前 Dashboard 逻辑

### 8.1 操作区按钮
- 刷新实时行情
- 刷新历史 K 线
- 生成信号
- 生成评分
- 一键完整刷新

### 8.2 顶部状态
- 数据源
- 最近刷新时间
- 股票池数量
- 实时行情数量
- 历史K线提示

### 8.3 Top Watchlist
- 主页面显著显示 `GET /watchlist/top?limit=50` 结果；
- 支持核心列与风险状态显示。

### 8.4 筛选器
- sector / policy_theme / concept_purity
- minimum total_score
- risk_penalty 上限

### 8.5 辅助表格
- snapshot / movers / signals / scores / watchlist / backtest
- 便于调试 payload 与展示一致性。

### 8.6 `normalize_records` 作用
统一处理 API 返回结构差异：
- list 直接用；
- dict 优先取 `data/items/results/snapshots/scores`；
- 都没有则包装成单行；
- 防止 DataFrame 渲染异常。

---

## 9. 当前已解决的问题（工程层）

1. 真实源在代理环境被阻断时可切换 mock；
2. Sina 抓取增加 headers 与批量逻辑；
3. history 刷新不再默认强制走 `push2his.eastmoney.com`；
4. `daily_bars.name` 空值导致 NOT NULL 报错已通过回填链解决；
5. NaN/inf 导致 JSON 序列化报错已修复；
6. score NaN 入库导致 NOT NULL 报错已修复；
7. Dashboard DataFrame payload 兼容错误已修复；
8. watchlist 有数据但前端不显示的问题已修复。

---

## 10. 当前仍存在的不足（实事求是）

1. 资金流仍以 proxy/规则为主，不是券商级主力净流入逐笔口径；
2. `fundamental_quality` 主要来自静态标签，非实时财报计算；
3. `concept_purity` 仍是规则化标签，非全量公告/订单验证；
4. `policy_theme` 仍有静态维护成分；
5. 仍未系统接入高质量财报、专利、研发人员结构数据源；
6. 回测结论受数据质量与简化假设影响，需谨慎解读；
7. 本系统不构成投资建议，也不应直接用于自动下单。

---

## 11. 下一步路线图（建议）

### Phase A：真实资金流
- 接入更稳定的主力资金净流入原始字段；
- 与当前 proxy 并行校验偏差。

### Phase B：真实低位结构
- 引入更严格的结构识别（波段结构、平台突破、假突破过滤）；
- 增加跨周期一致性检查。

### Phase C：Theme Research Engine 深化
- 从 v1 规则引擎升级到可维护的主题知识图谱；
- 增强主题迁移与主题强弱时序跟踪。

### Phase D：财报/专利/研发数据接入
- 接入研发费用率、研发人员占比、专利明细与质量指标；
- 支持“研究强度/创新强度/产业地位”半自动更新。

### Phase E：更严谨回测与风控
- 引入更严格的交易可达性约束、滑点、涨跌停/停牌约束；
- 做多周期稳健性、分市场环境稳健性检验。

---

## 12. 用户本地使用流程

### 12.1 创建并激活虚拟环境
```bash
python -m venv .venv
source .venv/bin/activate
```

### 12.2 安装依赖
```bash
pip install -r requirements.txt
```

### 12.3 配置环境变量
```bash
cp .env.example .env
# 编辑 .env，典型：
# USE_MOCK_DATA=false
# REAL_DATA_SOURCE=sina
```

### 12.4 初始化数据库
```bash
python scripts/init_db.py
```

### 12.5 启动 FastAPI
```bash
uvicorn app.main:app --reload
```

### 12.6 启动 Streamlit
```bash
streamlit run dashboard/streamlit_app.py
```

### 12.7 运行操作顺序（推荐）
1. 刷新实时行情（`/market/refresh`）
2. 刷新历史K线（`/history/refresh?days=120`）
3. 生成信号（`/signals/generate`）
4. 生成评分（`/scores/generate`）
5. 查看观察池（`/watchlist/top?limit=20`）

---

## 结论

当前 `tech-stock-monitor` 已具备“可运行、可落库、可解释、可视化”的研究监控骨架。  
但它仍是**研究工具**，不是预测系统，更不是自动交易系统。后续价值在于持续提升数据质量、主题研究深度与回测严谨性。
