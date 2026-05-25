from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.factors.liquidity import add_liquidity_factors
from app.factors.relative_strength import add_relative_strength_factors
from app.factors.technical import add_technical_factors
from app.models import DailyBar, StockScore, StockSignal
from app.scoring.score_engine import compute_score
from app.signals.signal_engine import generate_signals


class AnalysisService:
    def _latest_rows(self, db: Session) -> list[dict]:
        codes = [x[0] for x in db.query(DailyBar.code).group_by(DailyBar.code).all()]
        rows = []
        for code in codes:
            bars = db.query(DailyBar).filter_by(code=code).order_by(DailyBar.trade_date.asc()).all()
            if len(bars) < 25:
                continue
            d = pd.DataFrame([{"code":b.code,"name":b.name,"trade_date":b.trade_date,"close":b.close,"volume":b.volume,"amount":b.amount,"turnover_rate":b.turnover_rate} for b in bars])
            d = add_technical_factors(d)
            d = add_liquidity_factors(d)
            d = add_relative_strength_factors(d)
            rows.append(d.iloc[-1].to_dict())
        return rows

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
        scored = []
        for r in rows:
            s = compute_score(r)
            scored.append({"code":r["code"],"name":r["name"],**s})
        scored.sort(key=lambda x: x["total_score"], reverse=True)
        inserted = 0
        for i, s in enumerate(scored, start=1):
            payload = {**s, "rank": i, "trade_date": td, "reasons": json.dumps(s["reasons"], ensure_ascii=False)}
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
        return [{"code":x.code,"name":x.name,"total_score":x.total_score,"trend_score":x.trend_score,"momentum_score":x.momentum_score,"relative_strength_score":x.relative_strength_score,"liquidity_score":x.liquidity_score,"position_score":x.position_score,"risk_penalty":x.risk_penalty,"rank":x.rank,"reasons":json.loads(x.reasons)} for x in res]
