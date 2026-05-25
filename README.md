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
