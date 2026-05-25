import os

from app.services.history_data_service import HistoryDataService


def test_history_source_manual_injection():
    class X: ...
    svc = HistoryDataService(source=X())
    assert svc.source is not None


def test_history_source_has_name():
    os.environ['USE_MOCK_DATA'] = 'true'
    svc = HistoryDataService()
    assert hasattr(svc, 'source_name')
