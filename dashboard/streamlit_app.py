from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from app.config import get_settings
from app.universe.tech_universe import load_tech_universe_df


STATUS_COLOR = {
    "重点观察": "🟢",
    "普通观察": "🟡",
    "高风险": "🔴",
}


def fetch(url: str, method: str = "get"):
    try:
        resp = requests.request(method, url, timeout=120)
        resp.raise_for_status()
        return resp.json(), None, resp.status_code
    except Exception as exc:
        status_code = None
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            status_code = exc.response.status_code
        return None, str(exc), status_code


def resolve_data_source(base: str, settings_source: str) -> str:
    # Prefer backend-reported source from / (SystemStatusResponse).
    status_payload, _, _ = fetch(f"{base}/")
    if isinstance(status_payload, dict):
        backend_source = status_payload.get("data_source")
        if isinstance(backend_source, str) and backend_source.strip():
            return backend_source.strip().upper()

    # /health currently only returns status, keep as compatibility probe only.
    health_payload, _, _ = fetch(f"{base}/health")
    if isinstance(health_payload, dict):
        health_source = health_payload.get("data_source") or health_payload.get("real_data_source")
        if isinstance(health_source, str) and health_source.strip():
            return health_source.strip().upper()

    # Fallback to environment variable, then local settings.
    env_source = os.getenv("REAL_DATA_SOURCE")
    if isinstance(env_source, str) and env_source.strip():
        return env_source.strip().upper()

    return str(settings_source or "").strip().upper() or "UNKNOWN"


def _to_df(obj) -> pd.DataFrame:
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, list):
        return pd.DataFrame(obj)
    if isinstance(obj, dict):
        return pd.DataFrame([obj])
    return pd.DataFrame()


def normalize_records(payload) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "snapshots", "scores"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return []


def _format_reasons(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(str(x) for x in value)
    if isinstance(value, dict):
        return "；".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return "；".join(str(x) for x in parsed)
            if isinstance(parsed, dict):
                return "；".join(f"{k}: {v}" for k, v in parsed.items())
        except Exception:
            return value
        return value
    return str(value)


def _df_from_payload(payload) -> pd.DataFrame:
    records = normalize_records(payload)
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "reasons" in df.columns:
        df["reasons"] = df["reasons"].map(_format_reasons)
    if "reason" in df.columns:
        df["reason"] = df["reason"].map(_format_reasons)
    return df


def _watch_flag(total_score: float, risk_penalty: float) -> str:
    if risk_penalty >= 20:
        return f"{STATUS_COLOR['高风险']} 高风险"
    if total_score >= 75:
        return f"{STATUS_COLOR['重点观察']} 重点观察"
    if total_score >= 60:
        return f"{STATUS_COLOR['普通观察']} 普通观察"
    return "⚪ 观察"


def main():
    s = get_settings()
    base = f"http://{s.app_host}:{s.app_port}"

    st.set_page_config(page_title="主板科技低位转强监控器", layout="wide")
    st.title("主板科技低位转强监控器")
    active_source = resolve_data_source(base, s.data_source_provider)

    mode = "MOCK" if s.use_mock_data else "REAL"
    st.caption(f"数据模式: **{mode}** | REAL_DATA_SOURCE: **{active_source}**")
    if s.use_mock_data:
        st.warning("当前为演示数据，不可用于投资判断")

    # --- operations ---
    st.subheader("操作区")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

    refresh_result = {}
    if c1.button("刷新实时行情", use_container_width=True):
        d, e, c = fetch(f"{base}/market/refresh", method="post")
        refresh_result["market"] = (d, e, c)
    if c2.button("刷新历史K线", use_container_width=True):
        d, e, c = fetch(f"{base}/history/refresh?days=120", method="post")
        refresh_result["history"] = (d, e, c)
    if c3.button("生成信号", use_container_width=True):
        d, e, c = fetch(f"{base}/signals/generate", method="post")
        refresh_result["signals"] = (d, e, c)
    if c4.button("生成评分", use_container_width=True):
        d, e, c = fetch(f"{base}/scores/generate", method="post")
        refresh_result["scores"] = (d, e, c)
    if c5.button("一键完整刷新", use_container_width=True):
        d1, e1, c1 = fetch(f"{base}/market/refresh", method="post")
        d2, e2, c2 = fetch(f"{base}/history/refresh?days=120", method="post")
        d3, e3, c3 = fetch(f"{base}/signals/generate", method="post")
        d4, e4, c4 = fetch(f"{base}/scores/generate", method="post")
        refresh_result = {
            "market": (d1, e1, c1),
            "history": (d2, e2, c2),
            "signals": (d3, e3, c3),
            "scores": (d4, e4, c4),
        }
    if c6.button("AI 验证 Top10", use_container_width=True):
        d, e, c = fetch(f"{base}/agent/analyze-top", method="post")
        refresh_result["ai_top10"] = (d, e, c)
    if c7.button("每日市场情报", use_container_width=True):
        d, e, c = fetch(f"{base}/agent/daily-market", method="post")
        refresh_result["daily_market"] = (d, e, c)

    for key, (data, err, status_code) in refresh_result.items():
        if err:
            st.error(f"{key}: {err} (status_code={status_code})")
        else:
            st.success(f"{key}: {data}")
    if "ai_top10" in refresh_result and not refresh_result["ai_top10"][1]:
        ai_items = normalize_records(refresh_result["ai_top10"][0].get("items") if isinstance(refresh_result["ai_top10"][0], dict) else refresh_result["ai_top10"][0])
        if ai_items:
            ai_df = pd.DataFrame(ai_items)
            if "ai_reasons" in ai_df.columns:
                ai_df["ai_reasons"] = ai_df["ai_reasons"].map(_format_reasons)
            st.subheader("AI 验证 Top10 结果")
            st.dataframe(
                ai_df[[c for c in ["original_rank", "new_rank", "code", "name", "original_score", "ai_adjusted_score", "ai_sentiment_score", "ai_confidence", "ai_reasons"] if c in ai_df.columns]],
                use_container_width=True,
            )
    daily_market_json, _, _ = fetch(f"{base}/agent/daily-market/latest")
    if isinstance(daily_market_json, dict):
        st.subheader("每日市场情报")
        st.caption(daily_market_json.get("market_summary", ""))
        cnews, cstk = st.columns(2)
        with cnews:
            st.markdown("**5 条关键新闻**")
            news_df = pd.DataFrame(daily_market_json.get("top_news_json", []))
            if not news_df.empty:
                st.dataframe(news_df[[c for c in ["title", "impact_direction", "impact_horizon", "affected_sectors", "affected_themes", "reason"] if c in news_df.columns]], use_container_width=True)
            else:
                st.info("暂无市场情报新闻")
        with cstk:
            st.markdown("**相关股票 Top5**")
            rel_df = pd.DataFrame(daily_market_json.get("related_stocks_json", []))
            if not rel_df.empty:
                st.dataframe(rel_df[[c for c in ["code", "name", "relevance_score", "matched_themes", "matched_news_titles", "reason"] if c in rel_df.columns]], use_container_width=True)
            else:
                st.info("暂无映射股票")
        risks = daily_market_json.get("risk_notes", [])
        if risks:
            st.warning("；".join(str(x) for x in risks))

    # --- fetch current datasets for dashboard ---
    snapshot_json, snapshot_err, snapshot_status = fetch(f"{base}/market/snapshot")
    watch_json, watch_err, watch_status = fetch(f"{base}/watchlist/top?limit=50")
    signals_json, signals_err, signals_status = fetch(f"{base}/signals/latest")

    snapshot_df = _df_from_payload(snapshot_json)
    watch_df = _df_from_payload(watch_json)
    signals_df = _df_from_payload(signals_json)

    scores_json, scores_err, scores_status = fetch(f"{base}/scores/latest")
    movers_json, movers_err, movers_status = fetch(f"{base}/market/top-movers?limit=20")
    backtest_json, backtest_err, backtest_status = fetch(f"{base}/backtest/results/latest")
    scores_df = _df_from_payload(scores_json)
    movers_df = _df_from_payload(movers_json)
    backtest_df = _df_from_payload(backtest_json)

    universe_df = load_tech_universe_df()
    universe_count = len(universe_df)

    # enrich watchlist with universe metadata for filters/details
    if not watch_df.empty:
        watch_df["code"] = watch_df["code"].astype(str)
        watch_df["reasons_text"] = watch_df.get("reasons", "").map(_format_reasons)
        watch_df = watch_df.merge(
            universe_df[["code", "sector", "policy_theme", "concept_purity", "fundamental_quality"]],
            on="code",
            how="left",
        )
        watch_df["status"] = watch_df.apply(
            lambda r: _watch_flag(float(r.get("total_score", 0) or 0), float(r.get("risk_penalty", 0) or 0)),
            axis=1,
        )

    # --- top status bar ---
    st.subheader("顶部状态")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("数据源", active_source)
    m2.metric("最近刷新时间", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    m3.metric("股票池数量", universe_count)
    m4.metric("实时行情数量", len(snapshot_df))
    m5.metric("历史K线数量", "见 /history/refresh 返回")

    if snapshot_err:
        st.error(f"market/snapshot 读取失败: {snapshot_err} (status_code={snapshot_status})")
    if watch_err:
        st.error(f"watchlist/top 读取失败: {watch_err} (status_code={watch_status})")
    if signals_err:
        st.error(f"signals/latest 读取失败: {signals_err} (status_code={signals_status})")
    if scores_err:
        st.error(f"scores/latest 读取失败: {scores_err} (status_code={scores_status})")
    if movers_err:
        st.error(f"market/top-movers 读取失败: {movers_err} (status_code={movers_status})")
    if backtest_err:
        st.error(f"backtest/results/latest 读取失败: {backtest_err} (status_code={backtest_status})")

    with st.expander("辅助表格（统一 normalize_records 渲染）", expanded=False):
        st.markdown("**Market Snapshot**")
        st.dataframe(pd.DataFrame(normalize_records(snapshot_json)), use_container_width=True)
        st.markdown("**Top Movers**")
        st.dataframe(pd.DataFrame(normalize_records(movers_json)), use_container_width=True)
        st.markdown("**Signals**")
        st.dataframe(pd.DataFrame(normalize_records(signals_json)), use_container_width=True)
        st.markdown("**Scores**")
        st.dataframe(pd.DataFrame(normalize_records(scores_json)), use_container_width=True)
        st.markdown("**Watchlist**")
        st.dataframe(pd.DataFrame(normalize_records(watch_json)), use_container_width=True)
        st.markdown("**Backtest Results**")
        st.dataframe(pd.DataFrame(normalize_records(backtest_json)), use_container_width=True)

    st.divider()
    st.subheader("Top Watchlist")

    if watch_df.empty:
        st.info("暂无评分数据，请先点击“生成评分”或“一键完整刷新”。")
    else:
        # filters
        f1, f2, f3, f4, f5 = st.columns(5)
        sector_options = ["全部"] + sorted([x for x in watch_df["sector"].dropna().unique().tolist()])
        policy_options = ["全部"] + sorted([x for x in watch_df["policy_theme"].dropna().unique().tolist()])
        concept_options = ["全部"] + sorted([x for x in watch_df["concept_purity"].dropna().unique().tolist()])

        sector_sel = f1.selectbox("sector", sector_options, index=0)
        policy_sel = f2.selectbox("policy_theme", policy_options, index=0)
        concept_sel = f3.selectbox("concept_purity", concept_options, index=0)
        min_score = f4.slider("minimum total_score", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
        max_risk = f5.slider("排除 risk_penalty 过高", min_value=0.0, max_value=100.0, value=30.0, step=1.0)

        raw_count = len(watch_df)
        filtered = watch_df.copy()
        if sector_sel != "全部":
            filtered = filtered[filtered["sector"] == sector_sel]
        if policy_sel != "全部":
            filtered = filtered[filtered["policy_theme"] == policy_sel]
        if concept_sel != "全部":
            filtered = filtered[filtered["concept_purity"] == concept_sel]
        filtered = filtered[(filtered["total_score"] >= min_score) & (filtered["risk_penalty"] <= max_risk)]

        show_cols = [
            "status",
            "rank",
            "code",
            "name",
            "total_score",
            "percentile_250d",
            "consolidation_days",
            "ma_structure_score",
            "position_score",  # low_position_score mapping
            "recent_strength_score",
            "ma20_slope",
            "ma60_slope",
            "net_inflow_5d",
            "amount_ratio_5d",
            "trend_score",
            "momentum_score",  # capital_flow_score mapping
            "relative_strength_score",
            "liquidity_score",
            "risk_penalty",
            "reasons_text",
        ]
        rename_map = {
            "position_score": "low_position_score",
            "momentum_score": "capital_flow_score",
            "reasons_text": "reasons",
        }

        display_df = filtered[[c for c in show_cols if c in filtered.columns]].rename(columns=rename_map)
        st.caption(f"raw_count={raw_count} | filtered_count={len(filtered)} | score_count={len(display_df)}")
        if raw_count > 0 and len(display_df) == 0:
            st.warning("当前筛选条件过严，请降低 minimum total_score 或放宽 risk_penalty。")
        if filtered.shape[0] > 0 and display_df.empty:
            st.warning("watchlist records 非空但 DataFrame 为空，显示 raw payload 供排查")
            st.json(watch_json)
        st.dataframe(display_df, use_container_width=True, height=420)

        st.subheader("个股详情")
        codes = display_df["code"].astype(str).tolist()
        selected_code = st.selectbox("选择股票", options=codes)
        selected = filtered[filtered["code"].astype(str) == str(selected_code)]
        if not selected.empty:
            row = selected.iloc[0]
            d1, d2 = st.columns([1, 1])
            with d1:
                st.markdown(f"**{row.get('name','')} ({row.get('code','')})**")
                st.write("评分拆解")
                st.json(
                    {
                        "total_score": row.get("total_score"),
                        "trend_reversal_score": row.get("trend_score"),
                        "capital_inflow_score": row.get("momentum_score"),
                        "policy_alignment_score": row.get("relative_strength_score"),
                        "liquidity_score": row.get("liquidity_score"),
                        "low_position_score": row.get("position_score"),
                        "risk_penalty": row.get("risk_penalty"),
                    }
                )
                st.write("reasons")
                st.write(_format_reasons(row.get("reasons")))

                pos = float(row.get("position_score", 0) or 0)
                if pos >= 70:
                    st.info("近120日位置说明：处于相对低位并出现修复特征。")
                elif pos >= 40:
                    st.info("近120日位置说明：中位区域，仍需确认趋势延续。")
                else:
                    st.warning("近120日位置说明：位置优势不明显或历史区间不足。")

            with d2:
                sig = signals_df[signals_df["code"].astype(str) == str(selected_code)] if not signals_df.empty else pd.DataFrame()
                st.write("最近信号")
                if sig.empty:
                    st.caption("暂无信号")
                else:
                    sig = sig.copy()
                    sig["reason"] = sig["reason"].map(_format_reasons)
                    st.dataframe(sig[[c for c in ["signal_name", "signal_type", "strength", "reason", "generated_at"] if c in sig.columns]], use_container_width=True)

                px = snapshot_df[snapshot_df["code"].astype(str) == str(selected_code)] if not snapshot_df.empty else pd.DataFrame()
                st.write("最近价格")
                if px.empty:
                    st.caption("暂无实时行情")
                else:
                    st.dataframe(px[[c for c in ["code", "name", "price", "pct_change", "amount", "timestamp"] if c in px.columns]], use_container_width=True)


if __name__ == "__main__":
    main()
