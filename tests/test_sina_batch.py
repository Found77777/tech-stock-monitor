from app.data_sources.sina_source import SinaDataSource


def test_sina_batch_symbol_format():
    s = SinaDataSource()
    syms = [f"600{100+i:03d}" for i in range(120)]
    conv = [s._to_sina_symbol(x) for x in syms]
    assert all(x.startswith('sh') or x.startswith('sz') for x in conv)
    assert len(conv) == 120
