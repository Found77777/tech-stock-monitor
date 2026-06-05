# Cleanup Report

Generated: 2026-06-03

## Methodology

This report is a static-analysis review only. No code was deleted or refactored. The analysis used:

- `find .. -name AGENTS.md -print` to check repository instructions.
- `git status --short` to confirm the starting worktree state.
- `rg -n` searches across `app/`, `tests/`, `scripts/`, `README.md`, and `.env.example` for symbol and configuration references.
- Targeted source inspection of provider, service, scoring, data-source, research, diagnostics, and frontend files.

Caveat: Python projects can use dynamic imports and framework discovery, so “unused” means “no static references found in this repository” unless otherwise noted.

---

## A. Definitely Unused（高置信度未引用）

| Item | File path | Why it appears unused | Reference chain analysis | Deletion risk |
| --- | --- | --- | --- | --- |
| Tushare data source skeleton | `app/data_sources/tushare_source.py` | The class is not wired into the active provider, no tests import it, and `TushareDataSource` only appears at its own definition. It also defines `get_daily_bars()` rather than the active `BaseDataSource.fetch_daily_bars()` contract, so it is not currently instantiable as a concrete provider. | `MarketDataService` and `HistoryDataService` resolve sources through `app/data_sources/provider.py`; that provider supports `efinance`, `sina`, `akshare`, `pytdx`, and `mock`, but not `tushare`. `.env.example` contains `TUSHARE_TOKEN`, yet no runtime path reads it for data fetching. | Low for runtime; Medium if Tushare support is planned. |
| `SignalItem` schema | `app/schemas.py` | `SignalItem` has no static references outside its own class definition. | API routes import/use `HealthResponse`, `SystemStatusResponse`, and `UniverseItem`; `SignalItem` is not referenced by `app/api/*`, services, or tests. | Low. |
| Research helper: information coefficient | `app/research/factor_ic.py` | Function `information_coefficient()` only appears at its definition. | Active IC/backtest APIs use `app/backtest/factor_test.py` via `BacktestService`; no runtime or test path imports `app.research.factor_ic`. | Low to Medium; it may be retained as a research placeholder. |
| Research helper: factor sanity backtest | `app/research/factor_backtest.py` | Function `backtest_sanity()` only appears at its definition. | Active factor backtests are implemented in `app/backtest/factor_test.py` and `app/services/backtest_service.py`. No current route imports this research helper. | Low to Medium. |
| Research helper: regime bucket performance | `app/research/regime_performance.py` | Function `regime_bucket_performance()` only appears at its definition. | The current API/service layer does not call this module, and tests do not import it. | Low to Medium. |
| Research helper: event excess return | `app/research/event_study.py` | Function `event_excess_return()` only appears at its definition. | Event-style testing is implemented through `app/backtest/signal_test.py::signal_event_study`; no current path imports `app.research.event_study`. | Low to Medium. |
| Research helper: alpha decay | `app/research/alpha_decay.py` | Function `decay_curve()` only appears at its definition. | No scoring, backtest, API, or test path imports this function. | Low to Medium. |
| Diagnostics helper: factor correlation | `app/diagnostics/factor_correlation.py` | Function `factor_correlation_matrix()` only appears at its definition. | No API/service/backtest route imports it; current factor scoring does not invoke diagnostics. | Low to Medium. |
| Diagnostics helper: factor importance | `app/diagnostics/factor_importance.py` | Function `attribution_report()` only appears at its definition. | No runtime or test import was found. | Low to Medium. |
| Diagnostics helper: factor stability | `app/diagnostics/factor_stability.py` | Function `rolling_stability()` only appears at its definition. | No runtime or test import was found. | Low to Medium. |
| Diagnostics helper: factor clustering | `app/diagnostics/factor_cluster.py` | Function `cluster_from_correlation()` only appears at its definition. | No runtime or test import was found. | Low to Medium. |
| Diagnostics helper: redundancy adjustment | `app/diagnostics/redundancy_adjustment.py` | Function `effective_factor_count()` only appears at its definition. | `ENABLE_FACTOR_REDUNDANCY_ADJUSTMENT` is parsed in settings and tested, but no scoring path imports this helper or applies redundancy adjustment. | Medium, because the environment flag suggests an intended feature. |

---

## B. Probably Unused（可能未引用）

| Item | File path | Why it appears unused | Reference chain analysis | Deletion risk |
| --- | --- | --- | --- | --- |
| Regime engine and metrics | `app/regime/market_regime_engine.py`, `app/regime/*_metrics.py` | `MarketRegimeEngine` is referenced by `tests/test_research_architecture.py`, but no API route, scoring engine, signal engine, scheduler, or service invokes it. | Test-only reference chain: `tests/test_research_architecture.py` imports and instantiates `MarketRegimeEngine`. Runtime reference chain: none found. | Medium; likely planned architecture, not live pipeline. |
| Unified confidence helpers | `app/confidence/unified_confidence.py` | `calibrate_confidence()` and `uncertainty_band()` are only referenced by architecture tests. | Test-only reference chain: `tests/test_research_architecture.py`. Runtime reference chain: none found. | Medium. |
| Explainability waterfall helper | `app/explainability/alpha_attribution.py` | `score_waterfall()` is only referenced by architecture tests. | Test-only reference chain: `tests/test_research_architecture.py`. Runtime reference chain: none found in API, scoring, or frontend serialization. | Medium. |
| Sina-symbol universe helper | `app/universe/tech_universe.py::get_tech_universe_sina_symbols` | The helper has no static call sites. | The active universe loader returns raw 6-digit codes through `get_tech_universe()`; Sina symbol conversion is performed inside `SinaDataSource` instead. | Low. |
| Data-source `get_basic_info()` methods | `app/data_sources/base.py`, `app/data_sources/*_source.py` | The abstract method and adapter implementations exist across data sources, but no current service/API path calls `get_basic_info()`. | `MarketDataService` uses `get_realtime_quotes()`; `HistoryDataService` uses `fetch_daily_bars()` / `get_history()`. No static call to `get_basic_info()` found. | Medium; could be useful for future metadata enrichment. |
| `calculate_mock_score()` helper | `app/scoring/score_engine.py` | It is exercised by `tests/test_scoring.py`, but the live score generation path calls `compute_score()`. | Test-only reference chain: `tests/test_scoring.py`. Runtime reference chain: no service/API use found. | Low to Medium; keep if it is intended as a public utility. |
| Unused concrete-source imports in history service | `app/services/history_data_service.py` | Imports `AKShareDataSource`, `MockDataSource`, `PytdxDataSource`, and `primary_source_name`, but the service resolves sources through `build_data_source()` and `_history_fallback_chain()`. | Runtime source chain is `build_data_source(name)`, not direct class construction from those imports. | Low if only imports are removed; no behavioral change expected. |
| Unused concrete-source imports in market service | `app/services/market_data_service.py` | Imports `AKShareDataSource` and `MockDataSource`, but source construction is delegated to `build_data_source()`. | Runtime source chain is `primary_source_name()` -> `fallback_chain()` -> `build_data_source()`. | Low if only imports are removed. |

---

## C. Duplicate Implementations（重复实现）

| Item | File path | Why it appears duplicated | Reference chain analysis | Cleanup risk |
| --- | --- | --- | --- | --- |
| Factor/backtest research helpers vs active backtest module | `app/research/factor_ic.py`, `app/research/factor_backtest.py`, `app/backtest/factor_test.py` | Both areas describe IC/factor sanity/backtest functionality, but only `app/backtest/factor_test.py` is wired into `BacktestService`. | Active chain: `app/api/routes.py` -> `BacktestService` -> `daily_ic_series`, `ic_summary`, `factor_group_test`. Research chain: no runtime imports. | Medium; consolidate only after deciding whether `app/research` is public API or scratch space. |
| Event-study helpers | `app/research/event_study.py`, `app/backtest/signal_test.py` | Both implement event-return/event-study style utilities. The backtest implementation is the active one. | Active chain: `BacktestService` imports `signal_event_study`. Research helper has no runtime import. | Medium. |
| Code normalization helpers | `app/api/agent_routes.py`, `app/data_sources/sina_source.py`, `app/data_sources/efinance_source.py`, `app/data_sources/efinance_capital_flow.py` | Multiple modules define `_norm_code()` or `norm_code()` to strip prefixes and keep six-digit symbols. | Routes, market data, history data, and capital flow each normalize independently. A shared helper would reduce drift. | Medium; symbol handling is high-impact and should be tested carefully if centralized. |
| Sina symbol conversion | `app/data_sources/sina_source.py`, `app/universe/tech_universe.py` | `SinaDataSource._to_sina_symbol()` and `to_sina_symbol()` implement the same `sh`/`sz` prefix rule. | Active chain uses `SinaDataSource._to_sina_symbol()`; universe helper is not called. | Low to Medium. |
| Safe numeric clamp helpers | `app/scoring/score_engine.py`, `app/agent/sentiment_scorer.py`, `app/themes/theme_scoring.py`, `app/services/analysis_service.py`, `app/review/service.py` | Several `_safe` / `_safe_float` helpers perform similar numeric conversion and clamping. | They are local implementations in independent modules. Shared utility could improve consistency, but behavior may differ by domain. | Medium. |
| Amount-estimation logic | `app/data_sources/sina_source.py`, `app/services/history_data_service.py`, `app/services/analysis_service.py`, `app/scoring/score_engine.py` | Amount estimation and detection of estimated amount are handled in multiple layers. | Sina history estimates amount; history service has fallback estimation; analysis service detects estimated amount; score engine emits reasons. | High; amount semantics affect liquidity scoring and should not be consolidated without regression tests. |

---

## D. Deprecated Data Sources（废弃/非推荐数据源）

| Item | File path | Status | Reference chain analysis | Deletion risk |
| --- | --- | --- | --- | --- |
| Tushare source | `app/data_sources/tushare_source.py` | Deprecated/placeholder. Not provider-wired and not documented as a selectable source. | No active chain. `.env.example` still exposes `TUSHARE_TOKEN`, but provider cannot select `tushare`. | Low for runtime; Medium for planned work. |
| AKShare source | `app/data_sources/akshare_source.py` | Supported but no longer recommended as default due network/EastMoney instability. | Active if `REAL_DATA_SOURCE=akshare` or fallback chain includes it; tests cover normalization. | High to delete; keep unless the config option is removed. |
| EFinance realtime/history source | `app/data_sources/efinance_source.py` | Supported but no longer recommended as default realtime/history source; efinance remains recommended for `get_history_bill` capital flow via a separate module. | Active if `REAL_DATA_SOURCE=efinance` or `HISTORY_DATA_SOURCE=efinance`; tests cover it. `app/data_sources/efinance_capital_flow.py` is not deprecated. | High to delete; keep for explicit config compatibility. |
| Pytdx source | `app/data_sources/pytdx_source.py` | Hidden/less-documented provider. The provider can build it, but `.env.example` and README recommended source list emphasize `efinance`, `sina`, `akshare`, and `mock`. | Active if `REAL_DATA_SOURCE=pytdx`; tests cover a fake subclass. | Medium to High; document or remove from provider deliberately. |
| Mock source | `app/data_sources/mock_source.py` | Not deprecated for tests/dev; should not be considered dead code. | Active in tests and when `REAL_DATA_SOURCE=mock`; also fallback terminal source. | High to delete; keep. |

---

## E. Unused Environment Variables（失效/疑似未使用配置项）

| Environment variable | File path | Why it appears unused | Reference chain analysis | Cleanup risk |
| --- | --- | --- | --- | --- |
| `DATA_SOURCE_PROVIDER` | `.env.example`, `app/config.py` | Parsed in settings/example, but active source selection uses `REAL_DATA_SOURCE` through `primary_source_name()` and `HISTORY_DATA_SOURCE` for history. | No provider/service branch reads `settings.data_source_provider`. | Low to Medium; could confuse operators because it looks like a live selector. |
| `TUSHARE_TOKEN` | `.env.example`, `app/config.py` | Parsed but no active Tushare provider path consumes it. | `TushareDataSource` is not in `build_data_source()` and has no API/service/test chain. | Low if Tushare remains disabled; Medium if planned. |
| `ENABLE_FACTOR_REDUNDANCY_ADJUSTMENT` | `.env.example`, `app/config.py` | Parsed and tested, but no scoring path applies redundancy adjustment. | The only related implementation, `app/diagnostics/redundancy_adjustment.py`, is not imported by scoring or services. | Medium; flag suggests a promised feature. |
| `APP_HOST` | `.env.example`, `app/config.py` | Parsed but not used by `app/main.py` or scripts to bind the server. | Runtime launch is usually via `uvicorn app.main:app`; no code reads `settings.app_host`. | Low. |
| `APP_PORT` | `.env.example`, `app/config.py` | Parsed but not used by `app/main.py` or scripts to bind the server. | Runtime launch is usually via `uvicorn app.main:app`; no code reads `settings.app_port`. | Low. |

Not flagged as unused: `CAPITAL_FLOW_TOP_N` is used by `app/api/agent_routes.py`; `SINA_USER_AGENT` and `SINA_COOKIE` are used by `SinaDataSource` request headers.

---

## F. Safe Cleanup Candidates（安全清理候选）

| Candidate | File path | Why it is a candidate | Reference chain analysis | Cleanup risk |
| --- | --- | --- | --- | --- |
| Remove or explicitly wire Tushare | `app/data_sources/tushare_source.py`, `.env.example`, `app/config.py` | Current code advertises a token but has no usable provider chain. | No active references from provider/services/tests. | Low if removed; Medium if future Tushare work is planned. |
| Remove unused `SignalItem` | `app/schemas.py` | No static references found. | No API route, service, or test uses it. | Low. |
| Remove unused direct imports from services | `app/services/history_data_service.py`, `app/services/market_data_service.py` | Source construction is centralized through `build_data_source()`, so direct concrete-class imports are redundant. | Service runtime calls provider functions, not those direct imports. | Low. |
| Move experimental research/diagnostics modules behind documented APIs or to examples | `app/research/*`, `app/diagnostics/*` | They are currently not called by live routes/services and overlap with active backtest modules. | No runtime import chain found. | Medium; useful for future research but not operational today. |
| Centralize symbol normalization | `app/api/agent_routes.py`, `app/data_sources/*`, `app/universe/tech_universe.py` | Multiple local helpers normalize codes and build Sina symbols. | Independent chains in API, history, realtime, and capital-flow code. | Medium; add tests before changing. |
| Centralize safe numeric conversion | `app/scoring/score_engine.py`, `app/agent/sentiment_scorer.py`, `app/themes/theme_scoring.py`, `app/services/analysis_service.py`, `app/review/service.py` | Several helpers perform similar float conversion/clamping. | Local utility chains; no shared abstraction. | Medium. |
| Decide whether Pytdx is supported or deprecated | `app/data_sources/pytdx_source.py`, `app/data_sources/provider.py`, README, `.env.example` | Provider supports `pytdx`, but user-facing config docs emphasize other sources. | Active only when explicitly selected; tests exist. | Medium to High; document first if keeping. |
| Keep generated dependency folders out of git | `frontend/node_modules/` if present locally | This is a generated local install artifact, not source code. | `.gitignore` should keep it untracked; do not commit. | Low. |

---

## Recommended Cleanup Order

1. Low-risk cleanup: remove unused imports and `SignalItem` after a quick `pytest -q` run.
2. Configuration cleanup: either remove or document `DATA_SOURCE_PROVIDER`, `APP_HOST`, `APP_PORT`, and `ENABLE_FACTOR_REDUNDANCY_ADJUSTMENT` behavior.
3. Data-source cleanup: decide whether Tushare and Pytdx are official, experimental, or deprecated.
4. Architecture cleanup: consolidate research/diagnostics with the active backtest/explainability APIs, or move them to a clearly marked experimental namespace.
5. Utility cleanup: centralize code normalization and numeric safety helpers only after adding focused regression tests.
