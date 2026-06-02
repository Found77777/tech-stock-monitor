from pathlib import Path


def test_frontend_capital_flow_badges_cover_new_sources():
    text = Path("frontend/components/source-badge.tsx").read_text()
    assert "真实资金流" in text
    assert "efinance资金流" in text
    assert "估算资金流，非真实" in text
    assert "真实资金流不可用" in text
    assert "未启用资金流" in text
