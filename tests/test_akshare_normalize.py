import pandas as pd

from app.data_sources.akshare_source import AKShareDataSource


def test_normalize_spot_df():
    raw = pd.DataFrame([{"代码": "600000", "名称": "测试半导体", "最新价": "10.2", "涨跌幅": "1.2", "涨跌额": "0.1", "成交量": "100", "成交额": "50000000", "换手率": "2.3", "市盈率-动态": "30", "市净率": "2", "总市值": "1000000000", "流通市值": "800000000"}])
    df = AKShareDataSource().normalize_spot_df(raw)
    assert set(["code","name","price","pct_change","change","volume","amount","turnover_rate","pe","pb","total_market_cap","float_market_cap"]).issubset(df.columns)
    assert df.iloc[0]["code"] == "600000"
