from app.universe.tech_universe import is_mainboard_code, load_tech_universe_df


def test_mainboard_code_filter():
    assert is_mainboard_code('600001')
    assert is_mainboard_code('002001')
    assert not is_mainboard_code('300001')
    assert not is_mainboard_code('688001')


def test_csv_universe_reading_and_schema():
    df = load_tech_universe_df()
    assert len(df) >= 150
    required = {'code','name','sector','theme','fundamental_quality','policy_theme','concept_purity','sina_symbol'}
    assert required.issubset(df.columns)


def test_no_placeholder_names_and_mainboard_only():
    df = load_tech_universe_df()
    assert not df['name'].astype(str).str.contains('科技标的').any()
    assert df['code'].map(is_mainboard_code).all()


def test_enum_values_valid():
    df = load_tech_universe_df()
    assert set(df['concept_purity'].unique()).issubset({'core','related','weak','hype'})
    assert set(df['fundamental_quality'].unique()).issubset({'strong','medium','weak'})
