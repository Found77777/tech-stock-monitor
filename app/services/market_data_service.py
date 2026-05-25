"""Market data service: fetch, normalize, filter and persist snapshots."""
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.akshare_source import AKShareDataSource
from app.data_sources.mock_source import MockDataSource
from app.data_sources.pytdx_source import PytdxDataSource
from app.data_sources.sina_source import SinaDataSource
from app.models import StockSnapshot
from app.universe.tech_universe import get_tech_universe_codes
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataService:
    def _build_default_source(self):
        if self.settings.use_mock_data:
            return MockDataSource()
        source = str(self.settings.real_data_source).lower()
        if source == "sina":
            return SinaDataSource()
        if source == "akshare":
            return AKShareDataSource()
        if source == "pytdx":
            return PytdxDataSource()
        if source == "mock":
            return MockDataSource()
        return AKShareDataSource()

    def __init__(self, source: AKShareDataSource | MockDataSource | None = None) -> None:
        self.settings = get_settings()
        self.source = source or self._build_default_source()

    @staticmethod
    def filter_tech_universe(df: pd.DataFrame, min_amount: float, keyword_col: str = "name") -> pd.DataFrame:
        f = df.copy()
        f = f[~f["name"].astype(str).str.contains(r"\*?ST", na=False)]
        f = f[f["code"].astype(str).str.startswith(("600","601","603","605","000","001","002"))]
        f = f[f["amount"] >= min_amount]
        return f

    def refresh_snapshot(self, db: Session) -> dict[str, Any]:
        logger.info("market refresh start mode=%s", "MOCK" if self.settings.use_mock_data else "REAL")
        universe_codes = get_tech_universe_codes() if not self.settings.use_mock_data else []
        df = self.source.get_realtime_quotes(universe_codes)
        raw_count = len(df)
        filtered = self.filter_tech_universe(df, self.settings.min_amount)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filtered = filtered.assign(timestamp=ts)

        inserted = 0
        for row in filtered.to_dict(orient="records"):
            exists = db.query(StockSnapshot).filter_by(code=row["code"], timestamp=row["timestamp"]).first()
            if exists:
                continue
            db.add(StockSnapshot(**row))
            inserted += 1
        db.commit()
        logger.info("market refresh done universe=%s raw=%s filtered=%s inserted=%s", len(universe_codes), raw_count, len(filtered), inserted)
        return {"universe_count": len(universe_codes) if universe_codes else raw_count, "raw_count": raw_count, "filtered_count": len(filtered), "inserted_count": inserted, "timestamp": ts}

    def latest_snapshot(self, db: Session) -> list[dict[str, Any]]:
        ts = db.query(StockSnapshot.timestamp).order_by(desc(StockSnapshot.timestamp)).limit(1).scalar()
        if not ts:
            return []
        rows = db.query(StockSnapshot).filter(StockSnapshot.timestamp == ts).order_by(desc(StockSnapshot.pct_change)).all()
        return [self._to_dict(r) for r in rows]

    def top_movers(self, db: Session, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
        latest = self.latest_snapshot(db)
        if not latest:
            return {"by_pct_change": [], "by_amount": [], "by_turnover": []}
        return {
            "by_pct_change": sorted(latest, key=lambda x: x["pct_change"], reverse=True)[:limit],
            "by_amount": sorted(latest, key=lambda x: x["amount"], reverse=True)[:limit],
            "by_turnover": sorted(latest, key=lambda x: (x["turnover_rate"] or 0), reverse=True)[:limit],
        }

    @staticmethod
    def _to_dict(r: StockSnapshot) -> dict[str, Any]:
        return {c: getattr(r, c) for c in ["code", "name", "price", "pct_change", "change", "volume", "amount", "turnover_rate", "pe", "pb", "total_market_cap", "float_market_cap", "timestamp"]}
