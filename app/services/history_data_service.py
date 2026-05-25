from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.akshare_source import AKShareDataSource
from app.data_sources.mock_source import MockDataSource
from app.models import DailyBar
from app.services.market_data_service import MarketDataService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HistoryDataService:
    def __init__(self, source: AKShareDataSource | MockDataSource | None = None) -> None:
        settings = get_settings()
        self.source = source or (MockDataSource() if settings.use_mock_data else AKShareDataSource())

    def refresh(self, db: Session, days: int = 120) -> dict:
        universe = MarketDataService().latest_snapshot(db)
        if not universe:
            universe = MarketDataService().source.get_realtime_quotes([]).to_dict(orient="records")[:80]
        end = datetime.now().date()
        start = end - timedelta(days=max(days * 2, 180))
        inserted = 0
        codes = [x["code"] for x in universe]
        for code in codes:
            bars = self.source.fetch_daily_bars(code=code, start_date=str(start), end_date=str(end))
            for row in bars.tail(days).to_dict(orient="records"):
                exists = db.query(DailyBar).filter_by(code=row["code"], trade_date=str(row["trade_date"])).first()
                if exists:
                    continue
                db.add(DailyBar(**{**row, "trade_date": str(row["trade_date"])}))
                inserted += 1
        db.commit()
        logger.info("history refresh done codes=%s inserted=%s", len(codes), inserted)
        return {"codes": len(codes), "inserted": inserted, "days": days}
