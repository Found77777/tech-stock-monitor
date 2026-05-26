import pandas as pd
import requests
import streamlit as st
import altair as alt
from app.config import get_settings

def fetch(url, method='get'):
    try:
        r=requests.request(method,url,timeout=90); r.raise_for_status(); return r.json(),None
    except Exception as e:
        return None,str(e)

def main():
    s=get_settings(); base=f"http://{s.app_host}:{s.app_port}"
    st.title('A股科技监控平台（Phase 4）')
    mode = 'MOCK' if s.use_mock_data else 'REAL'
    st.info(f'数据模式: {mode}')
    if s.use_mock_data:
        st.warning('当前为演示数据，不可用于投资判断')
    tabs=st.tabs(['市场快照','观察池Top20','信号列表','回测与因子验证'])
    with tabs[0]:
        d,e=fetch(f"{base}/market/snapshot"); st.error(e) if e else st.dataframe(pd.DataFrame(d))
    with tabs[1]:
        d,e=fetch(f"{base}/watchlist/top?limit=20"); st.error(e) if e else st.dataframe(pd.DataFrame(d))
    with tabs[2]:
        d,e=fetch(f"{base}/signals/latest"); st.error(e) if e else st.dataframe(pd.DataFrame(d))
    with tabs[3]:
        c1,c2,c3,c4=st.columns(4)
        if c1.button('因子IC'): fetch(f"{base}/backtest/factor-ic",'post')
        if c2.button('分组收益'): fetch(f"{base}/backtest/factor-groups",'post')
        if c3.button('信号研究'): fetch(f"{base}/backtest/signals",'post')
        if c4.button('TopScore回测'): fetch(f"{base}/backtest/top-score",'post')
        res,e=fetch(f"{base}/backtest/results/latest")
        if e: st.error(e)
        else:
            st.json(res)
            for r in res:
                if r['test_type']=='factor_ic':
                    one=next(iter(r['payload'].values())) if r['payload'] else {}
                    sers=one.get('daily_ic_series',[])
                    if sers:
                        df=pd.DataFrame(sers)
                        st.altair_chart(alt.Chart(df).mark_line().encode(x='trade_date:T',y='ic:Q'),use_container_width=True)
                if r['test_type']=='top_score':
                    nav=pd.DataFrame(r['payload'].get('nav_curve',[]))
                    if not nav.empty:
                        st.altair_chart(alt.Chart(nav).mark_line().encode(x='trade_date:T',y='nav:Q'),use_container_width=True)
                        st.dataframe(pd.DataFrame([r['payload'].get('metrics',{})]))

if __name__=='__main__': main()
