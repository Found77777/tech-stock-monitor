from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.akshare_source import AKShareDataSource
from app.data_sources.mock_source import MockDataSource
from app.data_sources.pytdx_source import PytdxDataSource
from app.data_sources.sina_source import SinaDataSource
from app.models import DailyBar
from app.services.market_data_service import MarketDataService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HistoryDataService:
    def __init__(self, source: AKShareDataSource | MockDataSource | SinaDataSource | PytdxDataSource | None = None) -> None:
        settings = get_settings()
        self.source_name = "manual"
        if source is not None:
            self.source = source
        elif settings.use_mock_data:
            self.source = MockDataSource(); self.source_name = "mock"
        else:
            src = str(settings.real_data_source).lower()
            if src == "sina":
                self.source = SinaDataSource(); self.source_name = "sina"
            elif src == "pytdx":
                self.source = PytdxDataSource(); self.source_name = "pytdx"
            elif src == "akshare":
                self.source = AKShareDataSource(); self.source_name = "akshare"
            else:
                self.source = AKShareDataSource(); self.source_name = "akshare"

    def refresh(self, db: Session, days: int = 120) -> dict:
        logger.info("HistoryDataService using source=%s", self.source_name)
        universe = MarketDataService().latest_snapshot(db)
        if not universe:
            universe = MarketDataService().source.get_realtime_quotes([]).to_dict(orient="records")[:80]
        end = datetime.now().date()
        start = end - timedelta(days=max(days * 2, 180))
        inserted = 0
        codes = [x["code"] for x in universe]
        for code in codes:
            bars = self.source.fetch_daily_bars(code=code, start_date=str(start), end_date=str(end))
            if bars is None or bars.empty:
                logger.warning("history bars empty code=%s source=%s", code, self.source_name)
                continue
            for row in bars.tail(days).to_dict(orient="records"):
                exists = db.query(DailyBar).filter_by(code=row["code"], trade_date=str(row["trade_date"])).first()
                if exists:
                    continue
                db.add(DailyBar(**{**row, "trade_date": str(row["trade_date"])}))
                inserted += 1
        db.commit()
        logger.info("history refresh done codes=%s inserted=%s", len(codes), inserted)
        return {"codes": len(codes), "inserted": inserted, "days": days, "source": self.source_name}
