from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.factors.liquidity import add_liquidity_factors
from app.factors.relative_strength import add_relative_strength_factors
from app.factors.technical import add_technical_factors
from app.models import DailyBar, StockScore, StockSignal, StockSnapshot
from app.scoring.score_engine import compute_score
from app.signals.signal_engine import generate_signals
from app.universe.tech_universe import load_tech_universe_df


class AnalysisService:
    @staticmethod
    def _safe_db_score(v):
        import math
        try:
            x=float(v)
        except Exception:
            return 0.0
        if math.isnan(x) or math.isinf(x):
            return 0.0
        if x < 0:
            return 0.0
        if x > 100:
            return 100.0
        return x

    def _latest_rows(self, db: Session) -> list[dict]:
        codes = [x[0] for x in db.query(DailyBar.code).group_by(DailyBar.code).all()]
        u_df = load_tech_universe_df().set_index("code")
        rows = []
        for code in codes:
            bars = db.query(DailyBar).filter_by(code=code).order_by(DailyBar.trade_date.asc()).all()
            if len(bars) < 25:
                continue
            d = pd.DataFrame([{"code":b.code,"name":b.name,"trade_date":b.trade_date,"close":b.close,"volume":b.volume,"amount":b.amount,"turnover_rate":b.turnover_rate} for b in bars])
            d = add_technical_factors(d)
            d = add_liquidity_factors(d)
            d = add_relative_strength_factors(d)
            row = d.iloc[-1].to_dict()
            if str(code) in u_df.index:
                for k, v in u_df.loc[str(code)].to_dict().items():
                    row[k] = v
            rows.append(row)
        return rows

    def _universe_name_map(self) -> dict[str, str]:
        try:
            df = load_tech_universe_df()
            return {
                str(r["code"]): str(r["name"])
                for r in df[["code", "name"]].to_dict(orient="records")
                if str(r.get("code", "")).strip() and str(r.get("name", "")).strip()
            }
        except Exception:
            return {}

    def _resolve_name(self, db: Session, code: str, row_name: str | None, universe_name_map: dict[str, str]) -> str:
        code = str(code)
        candidate = str(row_name).strip() if row_name is not None else ""
        if candidate and candidate != code:
            return candidate

        latest_snapshot_name = (
            db.query(StockSnapshot.name)
            .filter(StockSnapshot.code == code)
            .order_by(desc(StockSnapshot.timestamp))
            .first()
        )
        if latest_snapshot_name and str(latest_snapshot_name[0]).strip():
            return str(latest_snapshot_name[0]).strip()

        universe_name = universe_name_map.get(code, "")
        if str(universe_name).strip():
            return str(universe_name).strip()

        return code

    def generate_signals(self, db: Session) -> dict:
        rows = self._latest_rows(db)
        trade_date = datetime.now().strftime("%Y-%m-%d")
        inserted = 0
        for r in rows:
            for s in generate_signals(r):
                if db.query(StockSignal).filter_by(code=s["code"], trade_date=trade_date, signal_name=s["signal_name"]).first():
                    continue
                db.add(StockSignal(**s, trade_date=trade_date))
                inserted += 1
        db.commit()
        return {"rows": len(rows), "inserted": inserted}

    def latest_signals(self, db: Session) -> list[dict]:
        td = db.query(func.max(StockSignal.trade_date)).scalar()
        if not td:
            return []
        res = db.query(StockSignal).filter_by(trade_date=td).all()
        return [{"code":x.code,"name":x.name,"signal_name":x.signal_name,"signal_type":x.signal_type,"strength":x.strength,"reason":x.reason,"generated_at":x.generated_at} for x in res]

    def generate_scores(self, db: Session) -> dict:
        rows = self._latest_rows(db)
        td = datetime.now().strftime("%Y-%m-%d")
        universe_name_map = self._universe_name_map()
        scored = []
        for r in rows:
            s = compute_score(r)
            code = str(r["code"])
            resolved_name = self._resolve_name(db, code, r.get("name"), universe_name_map)
            scored.append({"code": code, "name": resolved_name, **s})
        scored.sort(key=lambda x: x["total_score"], reverse=True)
        inserted = 0
        for i, s in enumerate(scored, start=1):
            payload = {
                "code": s["code"],
                "name": s["name"],
                "total_score": s.get("total_score"),
                "trend_score": s.get("trend_score"),
                "momentum_score": s.get("momentum_score"),
                "relative_strength_score": s.get("relative_strength_score"),
                "liquidity_score": s.get("liquidity_score"),
                "position_score": s.get("position_score"),
                "risk_penalty": s.get("risk_penalty"),
                "rank": i,
                "trade_date": td,
                "reasons": json.dumps(s["reasons"], ensure_ascii=False),
            }
            payload["name"] = str(payload.get("name") or payload.get("code"))
            for k in ["total_score","trend_score","momentum_score","relative_strength_score","liquidity_score","position_score","risk_penalty"]:
                payload[k] = self._safe_db_score(payload.get(k))
            if db.query(StockScore).filter_by(code=s["code"], trade_date=td).first():
                continue
            db.add(StockScore(**payload))
            inserted += 1
        db.commit()
        return {"rows": len(rows), "inserted": inserted}

    def latest_scores(self, db: Session) -> list[dict]:
        td = db.query(func.max(StockScore.trade_date)).scalar()
        if not td:
            return []
        res = db.query(StockScore).filter_by(trade_date=td).order_by(desc(StockScore.total_score)).all()
        return [{"code":x.code,"name":x.name,"total_score":x.total_score,"trend_score":x.trend_score,"momentum_score":x.momentum_score,"relative_strength_score":x.relative_strength_score,"liquidity_score":x.liquidity_score,"position_score":x.position_score,"risk_penalty":x.risk_penalty,"recent_strength_score":x.momentum_score,"rank":x.rank,"reasons":json.loads(x.reasons)} for x in res]
