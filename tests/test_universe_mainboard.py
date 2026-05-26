from app.universe.tech_universe import is_mainboard_code, load_tech_universe_df


def test_mainboard_code_filter():
    assert is_mainboard_code('600001')
    assert is_mainboard_code('002001')
    assert not is_mainboard_code('300001')
    assert not is_mainboard_code('688001')


def test_csv_universe_reading():
    df = load_tech_universe_df()
    assert len(df) >= 150
    assert {'code','name','sector','theme','sina_symbol'}.issubset(df.columns)
