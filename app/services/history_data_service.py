from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.akshare_source import AKShareDataSource
from app.data_sources.mock_source import MockDataSource
from app.data_sources.pytdx_source import PytdxDataSource
from app.data_sources.sina_source import SinaDataSource
from app.models import DailyBar, StockSnapshot
from app.services.market_data_service import MarketDataService
from app.universe.tech_universe import load_tech_universe_df
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HistoryDataService:
    def __init__(self, source: AKShareDataSource | MockDataSource | SinaDataSource | PytdxDataSource | None = None) -> None:
        self.source = source
        self.source_name = "manual" if source is not None else "auto"

    def _resolve_source(self):
        settings = get_settings()
        if self.source is not None:
            return self.source, self.source_name
        if settings.use_mock_data:
            return MockDataSource(), "mock"
        src = str(settings.real_data_source).lower()
        if src == "sina":
            return SinaDataSource(), "sina"
        if src == "pytdx":
            return PytdxDataSource(), "pytdx"
        if src == "akshare":
            return AKShareDataSource(), "akshare"
        return AKShareDataSource(), "akshare"

    def _row_has_nested(self, row: dict) -> bool:
        for v in row.values():
            if isinstance(v, (dict, list, tuple)):
                return True
        return False

    @staticmethod
    def _universe_name_map() -> dict[str, str]:
        try:
            df = load_tech_universe_df()
            return {str(r["code"]): str(r["name"]) for _, r in df[["code", "name"]].iterrows()}
        except Exception:
            return {}

    def _resolve_name(self, db: Session, code: str, fallback_map: dict[str, str], row_name: str | None) -> str:
        if row_name and str(row_name).strip():
            return str(row_name)
        snap_name = (
            db.query(StockSnapshot.name)
            .filter(StockSnapshot.code == str(code), StockSnapshot.name.isnot(None))
            .order_by(StockSnapshot.timestamp.desc())
            .limit(1)
            .scalar()
        )
        if snap_name:
            return str(snap_name)
        if str(code) in fallback_map:
            return str(fallback_map[str(code)])
        return str(code)

    def refresh(self, db: Session, days: int = 120) -> dict:
        source, source_name = self._resolve_source()
        logger.info("HistoryDataService using source=%s", source_name)

        universe = MarketDataService().latest_snapshot(db)
        if not universe:
            universe = MarketDataService().source.get_realtime_quotes([]).to_dict(orient="records")[:80]

        end = datetime.now().date()
        start = end - timedelta(days=max(days * 2, 180))
        inserted = 0
        codes = [x["code"] for x in universe]
        name_map = self._universe_name_map()

        for code in codes:
            bars = source.fetch_daily_bars(code=code, start_date=str(start), end_date=str(end))
            if bars is None or bars.empty:
                logger.warning("history bars empty code=%s source=%s", code, source_name)
                continue
            for row in bars.tail(days).to_dict(orient="records"):
                if self._row_has_nested(row):
                    logger.warning("history row nested skipped code=%s source=%s row=%s", code, source_name, row)
                    continue
                row["code"] = str(row.get("code") or code)
                row["name"] = self._resolve_name(db, row["code"], name_map, row.get("name"))
                row["trade_date"] = str(row["trade_date"])
                exists = db.query(DailyBar).filter_by(code=row["code"], trade_date=row["trade_date"]).first()
                if exists:
                    continue
                db.add(DailyBar(**row))
                inserted += 1
        db.commit()
        logger.info("history refresh done codes=%s inserted=%s", len(codes), inserted)
        return {"codes": len(codes), "inserted": inserted, "days": days, "source": source_name}
