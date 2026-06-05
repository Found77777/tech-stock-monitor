from pathlib import Path


def test_frontend_capital_flow_badges_cover_new_sources():
    text = Path("frontend/components/source-badge.tsx").read_text()
    assert "真实资金流" in text
    assert "efinance历史资金流" in text
    assert "Sina量价资金强度" in text
    assert "基于成交额、成交量和价格共振估算，不代表真实主力资金流" in text
    assert "Proxy估算，非真实资金流" in text
    assert "资金流不可用" in text
    assert "未验证资金流" in text
    assert "未启用资金流" in text
