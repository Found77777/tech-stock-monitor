"""Market data service: fetch, normalize, filter and persist snapshots."""
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.data_sources.akshare_source import AKShareDataSource
from app.data_sources.base import BaseDataSource
from app.data_sources.mock_source import MockDataSource
from app.data_sources.provider import build_data_source, fallback_chain, primary_source_name
from app.models import StockSnapshot
from app.universe.tech_universe import get_tech_universe_codes
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataService:
    def _build_default_source(self) -> BaseDataSource:
        name = primary_source_name()
        logger.info("Using market data source: %s", name)
        return build_data_source(name)

    def __init__(self, source: BaseDataSource | None = None) -> None:
        self.settings = get_settings()
        self.source = source or self._build_default_source()
        self.source_name = "manual" if source is not None else primary_source_name()

    def _fetch_realtime_with_fallback(self, universe_codes: list[str]) -> tuple[pd.DataFrame, str]:
        if self.source_name == "manual":
            return self.source.get_realtime_quotes(universe_codes), "manual"
        last_exc: Exception | None = None
        for source_name in fallback_chain(primary_source_name()):
            try:
                source = build_data_source(source_name)
                df = source.get_realtime_quotes(universe_codes)
                if df is None or df.empty:
                    raise ValueError("empty realtime quotes")
                if source_name != primary_source_name():
                    logger.warning("fallback source used primary=%s fallback=%s", primary_source_name(), source_name)
                self.source = source
                self.source_name = source_name
                return df, source_name
            except Exception as exc:
                last_exc = exc
                logger.warning("primary source failed source=%s err=%s", source_name, exc)
        raise RuntimeError(f"all market data sources failed: {last_exc}")

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
        df, data_source_used = self._fetch_realtime_with_fallback(universe_codes)
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
        logger.info("market refresh done source=%s universe=%s raw=%s filtered=%s inserted=%s", data_source_used, len(universe_codes), raw_count, len(filtered), inserted)
        return {"universe_count": len(universe_codes) if universe_codes else raw_count, "raw_count": raw_count, "filtered_count": len(filtered), "inserted_count": inserted, "timestamp": ts, "data_source_used": data_source_used}

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
