"""Technology stock universe module."""


def get_mock_tech_universe() -> list[dict[str, str]]:
    """Return a mock list of A-share tech-focused symbols."""
    return [
        {"symbol": "000063.SZ", "name": "中兴通讯", "sector": "通信设备"},
        {"symbol": "002371.SZ", "name": "北方华创", "sector": "半导体设备"},
        {"symbol": "300308.SZ", "name": "中际旭创", "sector": "AI算力"},
        {"symbol": "603986.SH", "name": "兆易创新", "sector": "半导体"},
        {"symbol": "002475.SZ", "name": "立讯精密", "sector": "消费电子"},
    ]
