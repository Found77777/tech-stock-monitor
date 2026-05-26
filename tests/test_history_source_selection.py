import os

from app.config import get_settings
from app.data_sources.sina_source import SinaDataSource
from app.services.history_data_service import HistoryDataService


def test_history_source_manual_injection():
    class X: ...
    svc = HistoryDataService(source=X())
    assert svc.source is not None


def test_history_source_has_name():
    os.environ['USE_MOCK_DATA'] = 'true'
    get_settings.cache_clear()
    svc = HistoryDataService()
    _, name = svc._resolve_source()
    assert name == 'mock'


def test_history_source_selects_sina_from_env():
    os.environ['USE_MOCK_DATA'] = 'false'
    os.environ['REAL_DATA_SOURCE'] = 'sina'
    get_settings.cache_clear()
    svc = HistoryDataService()
    source, name = svc._resolve_source()
    assert name == 'sina'
    assert isinstance(source, SinaDataSource)
