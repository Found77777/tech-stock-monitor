from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.backtest.factor_test import SCORE_COLS, add_forward_returns, daily_ic_series, factor_group_test, ic_summary
from app.backtest.portfolio_backtest import run_top_score_backtest
from app.backtest.signal_test import signal_event_study
from app.models import BacktestResult, DailyBar, StockScore, StockSignal


class BacktestService:
    def _bars_df(self, db: Session) -> pd.DataFrame:
        rows = db.query(DailyBar).all()
        return pd.DataFrame([{"code":x.code,"name":x.name,"trade_date":x.trade_date,"close":x.close} for x in rows])

    def _scores_df(self, db: Session) -> pd.DataFrame:
        rows = db.query(StockScore).all()
        return pd.DataFrame([{"code":x.code,"trade_date":x.trade_date,"total_score":x.total_score,"trend_score":x.trend_score,"momentum_score":x.momentum_score,"relative_strength_score":x.relative_strength_score,"liquidity_score":x.liquidity_score,"position_score":x.position_score} for x in rows])

    def run_factor_ic_test(self, db: Session) -> dict:
        b = self._bars_df(db)
        s = self._scores_df(db)
        df = s.merge(add_forward_returns(b)[["code","trade_date","forward_return_5d"]], on=["code","trade_date"], how="left")
        out = {}
        for col in SCORE_COLS:
            ic = daily_ic_series(df, col, "forward_return_5d", method="spearman")
            out[col] = {**ic_summary(ic), "daily_ic_series": [{"trade_date":str(i),"ic":float(v)} for i,v in ic.items()]}
        self._save(db, "factor_ic", out)
        return out

    def run_factor_group_test(self, db: Session, groups: int = 5) -> dict:
        b = add_forward_returns(self._bars_df(db))
        s = self._scores_df(db)
        df = s.merge(b[["code","trade_date","forward_return_5d","forward_return_20d"]], on=["code","trade_date"], how="left")
        out = {"forward_5d": factor_group_test(df, "total_score", "forward_return_5d", groups), "forward_20d": factor_group_test(df, "total_score", "forward_return_20d", groups)}
        self._save(db, "factor_groups", out)
        return out

    def run_signal_event_study(self, db: Session) -> list[dict]:
        sig = db.query(StockSignal).all()
        sdf = pd.DataFrame([{"code":x.code,"trade_date":x.trade_date,"signal_name":x.signal_name} for x in sig])
        out = signal_event_study(sdf, self._bars_df(db)) if not sdf.empty else []
        self._save(db, "signal_event", out)
        return out

    def run_top_score_backtest(self, db: Session, top_n: int = 20, hold_days: int = 5, transaction_cost_bps: float = 0.0) -> dict:
        out = run_top_score_backtest(self._scores_df(db), self._bars_df(db), top_n=top_n, hold_days=hold_days, transaction_cost_bps=transaction_cost_bps)
        self._save(db, "top_score", out)
        return out

    def latest_results(self, db: Session) -> list[dict]:
        rows = db.query(BacktestResult).order_by(desc(BacktestResult.id)).limit(10).all()
        return [{"test_type":x.test_type,"trade_date":x.trade_date,"payload":json.loads(x.payload)} for x in rows]

    def _save(self, db: Session, t: str, payload: dict | list) -> None:
        db.add(BacktestResult(test_type=t, trade_date=datetime.now().strftime("%Y-%m-%d"), payload=json.dumps(payload, ensure_ascii=False)))
        db.commit()
