from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models import DailyReview, TradeLog, TradePlan
from app.review.schemas import DailyReviewCreate, TradeLogCreate, TradePlanCreate


def _dump(value: Any) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def _load(value: str | None) -> list:
    if not value:
        return []
    try:
        data = json.loads(value)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _safe_float(v: Any) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    if x != x or x in (float("inf"), float("-inf")):
        return 0.0
    return x


def _norm_symbol(symbol: str) -> str:
    s = "".join(ch for ch in str(symbol or "") if ch.isdigit())
    return s[-6:].zfill(6) if s else ""


class ReviewService:
    def upsert_trade_plan(self, db: Session, payload: TradePlanCreate) -> dict:
        row = db.query(TradePlan).filter_by(trade_date=payload.trade_date).first()
        data = {
            "trade_date": payload.trade_date,
            "watch_symbols": _dump([_norm_symbol(x) for x in payload.watch_symbols if _norm_symbol(x)]),
            "focus_sectors": _dump(payload.focus_sectors),
            "market_view": payload.market_view,
            "bull_case": payload.bull_case,
            "bear_case": payload.bear_case,
            "max_position": _safe_float(payload.max_position),
            "planned_trades": _dump(payload.planned_trades),
            "risk_notes": _dump(payload.risk_notes),
        }
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = TradePlan(**data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return self.trade_plan_to_dict(row)

    def trade_plan_to_dict(self, row: TradePlan) -> dict:
        return {
            "id": row.id,
            "trade_date": row.trade_date,
            "watch_symbols": _load(row.watch_symbols),
            "focus_sectors": _load(row.focus_sectors),
            "market_view": row.market_view or "",
            "bull_case": row.bull_case or "",
            "bear_case": row.bear_case or "",
            "max_position": _safe_float(row.max_position),
            "planned_trades": _load(row.planned_trades),
            "risk_notes": _load(row.risk_notes),
        }

    def get_trade_plan(self, db: Session, trade_date: str) -> dict | None:
        row = db.query(TradePlan).filter_by(trade_date=trade_date).first()
        return self.trade_plan_to_dict(row) if row else None

    def upsert_daily_review(self, db: Session, payload: DailyReviewCreate) -> dict:
        row = db.query(DailyReview).filter_by(review_date=payload.review_date).first()
        data = {
            "review_date": payload.review_date,
            "status": payload.status,
            "market_score": _safe_float(payload.market_score),
            "market_environment": payload.market_environment,
            "emotion_score": _safe_float(payload.emotion_score),
            "execution_score": _safe_float(payload.execution_score),
            "discipline_score": _safe_float(payload.discipline_score),
            "daily_pnl": _safe_float(payload.daily_pnl),
            "max_drawdown": _safe_float(payload.max_drawdown),
            "largest_winner": payload.largest_winner,
            "largest_loser": payload.largest_loser,
            "mistakes": _dump(payload.mistakes),
            "good_decisions": _dump(payload.good_decisions),
            "lessons_learned": _dump(payload.lessons_learned),
            "tomorrow_plan": payload.tomorrow_plan,
        }
        if row:
            for k, v in data.items():
                setattr(row, k, v)
        else:
            row = DailyReview(**data)
            db.add(row)
        db.commit()
        db.refresh(row)
        return self.daily_review_to_dict(row)

    def daily_review_to_dict(self, row: DailyReview) -> dict:
        return {
            "id": row.id,
            "review_date": row.review_date,
            "status": row.status,
            "market_score": _safe_float(row.market_score),
            "market_environment": row.market_environment or "",
            "emotion_score": _safe_float(row.emotion_score),
            "execution_score": _safe_float(row.execution_score),
            "discipline_score": _safe_float(row.discipline_score),
            "daily_pnl": _safe_float(row.daily_pnl),
            "max_drawdown": _safe_float(row.max_drawdown),
            "largest_winner": row.largest_winner or "",
            "largest_loser": row.largest_loser or "",
            "mistakes": _load(row.mistakes),
            "good_decisions": _load(row.good_decisions),
            "lessons_learned": _load(row.lessons_learned),
            "tomorrow_plan": row.tomorrow_plan or "",
        }

    def get_daily_review(self, db: Session, review_date: str) -> dict | None:
        row = db.query(DailyReview).filter_by(review_date=review_date).first()
        return self.daily_review_to_dict(row) if row else None

    def create_review_draft(self, db: Session, review_date: str | None = None) -> dict:
        day = review_date or datetime.now().strftime("%Y-%m-%d")
        existing = db.query(DailyReview).filter_by(review_date=day).first()
        if existing:
            return self.daily_review_to_dict(existing)
        row = DailyReview(review_date=day, status="pending")
        db.add(row)
        db.commit()
        db.refresh(row)
        return self.daily_review_to_dict(row)

    def create_trade_log(self, db: Session, payload: TradeLogCreate) -> dict:
        row = TradeLog(
            trade_date=payload.trade_date,
            symbol=_norm_symbol(payload.symbol),
            action=payload.action.lower(),
            quantity=_safe_float(payload.quantity),
            entry_price=_safe_float(payload.entry_price),
            exit_price=_safe_float(payload.exit_price),
            pnl=_safe_float(payload.pnl),
            planned_trade="true" if payload.planned_trade else "false",
            actual_reason=payload.actual_reason,
            result_score=_safe_float(payload.result_score),
            notes=payload.notes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return self.trade_log_to_dict(row)

    def trade_log_to_dict(self, row: TradeLog) -> dict:
        return {
            "id": row.id,
            "trade_date": row.trade_date,
            "symbol": row.symbol,
            "action": row.action,
            "quantity": _safe_float(row.quantity),
            "entry_price": _safe_float(row.entry_price),
            "exit_price": _safe_float(row.exit_price),
            "pnl": _safe_float(row.pnl),
            "planned_trade": str(row.planned_trade).lower() == "true",
            "actual_reason": row.actual_reason or "",
            "result_score": _safe_float(row.result_score),
            "notes": row.notes or "",
        }

    def list_trade_logs(self, db: Session, trade_date: str) -> list[dict]:
        return [self.trade_log_to_dict(r) for r in db.query(TradeLog).filter_by(trade_date=trade_date).all()]

    def plan_drift(self, db: Session, trade_date: str) -> dict:
        plan = self.get_trade_plan(db, trade_date)
        logs = self.list_trade_logs(db, trade_date)
        violations: list[dict] = []
        planned_symbols = set(plan.get("watch_symbols", [])) if plan else set()
        planned_trades = plan.get("planned_trades", []) if plan else []
        planned_trade_symbols = {_norm_symbol(x.get("symbol", "")) for x in planned_trades if isinstance(x, dict)}
        allowed = {x for x in planned_symbols | planned_trade_symbols if x}
        traded = {x["symbol"] for x in logs}

        for symbol in sorted(allowed - traded):
            violations.append({"type": "missed_planned_trade", "symbol": symbol, "severity": 8, "message": "计划内标的未执行/未记录"})
        for log in logs:
            if allowed and log["symbol"] not in allowed:
                violations.append({"type": "unplanned_trade", "symbol": log["symbol"], "severity": 18, "message": "计划外交易"})
            if plan and log["quantity"] * log["entry_price"] > _safe_float(plan.get("max_position", 0)) > 0:
                violations.append({"type": "over_position", "symbol": log["symbol"], "severity": 20, "message": "超过计划最大仓位"})
            reason = f"{log.get('actual_reason','')} {log.get('notes','')}"
            if any(k in reason for k in ["追高", "冲动", "情绪", "FOMO"]):
                violations.append({"type": "emotional_trade", "symbol": log["symbol"], "severity": 15, "message": "疑似情绪/追高交易"})

        penalty = sum(int(v.get("severity", 0)) for v in violations)
        discipline_score = max(0.0, 100.0 - penalty)
        return {
            "discipline_score": discipline_score,
            "violations": violations,
            "summary": f"发现{len(violations)}项计划-执行偏差，纪律分{discipline_score:.0f}",
        }

    def ai_summary(self, db: Session, review_date: str) -> dict:
        review = self.get_daily_review(db, review_date) or self.create_review_draft(db, review_date)
        drift = self.plan_drift(db, review_date)
        logs = self.list_trade_logs(db, review_date)
        strengths = list(review.get("good_decisions", []))
        weaknesses = list(review.get("mistakes", []))
        if drift["violations"]:
            weaknesses.append("存在计划-执行偏差")
        pnl_values = [x["pnl"] for x in logs]
        risk_score = min(100.0, max(0.0, abs(_safe_float(review.get("max_drawdown", 0))) * 10 + len(drift["violations"]) * 8))
        suggestions = []
        if drift["discipline_score"] < 80:
            suggestions.append("盘中只允许执行盘前计划内交易，计划外交易需二次确认并记录原因")
        if pnl_values and sum(1 for x in pnl_values if x < 0) > sum(1 for x in pnl_values if x > 0):
            suggestions.append("复盘亏损交易的入场触发条件，降低低质量交易频率")
        if not suggestions:
            suggestions.append("保持交易计划、执行和复盘闭环，继续积累样本")
        repeated = [x for x in weaknesses if weaknesses.count(x) > 1]
        return {
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:5],
            "repeated_mistakes": sorted(set(repeated))[:5],
            "discipline_score": drift["discipline_score"],
            "risk_score": risk_score,
            "suggestions": suggestions[:5],
        }

    def stats(self, db: Session, days: int = 30) -> dict:
        rows = db.query(DailyReview).order_by(desc(DailyReview.review_date)).limit(days).all()
        reviews = [self.daily_review_to_dict(r) for r in rows]
        if not reviews:
            return {"days": 0, "win_rate": 0.0, "average_pnl": 0.0, "max_drawdown": 0.0, "average_discipline_score": 0.0, "consecutive_profit_days": 0, "consecutive_loss_days": 0}
        pnls = [r["daily_pnl"] for r in reviews]
        win_rate = sum(1 for x in pnls if x > 0) / len(pnls)
        avg_pnl = sum(pnls) / len(pnls)
        max_dd = min([r["max_drawdown"] for r in reviews] + [0.0])
        avg_disc = sum(r["discipline_score"] for r in reviews) / len(reviews)
        ordered = sorted(reviews, key=lambda x: x["review_date"])
        profit = loss = 0
        for r in ordered:
            if r["daily_pnl"] > 0:
                profit += 1; loss = 0
            elif r["daily_pnl"] < 0:
                loss += 1; profit = 0
            else:
                profit = loss = 0
        return {"days": len(reviews), "win_rate": round(win_rate, 4), "average_pnl": round(avg_pnl, 4), "max_drawdown": max_dd, "average_discipline_score": round(avg_disc, 4), "consecutive_profit_days": profit, "consecutive_loss_days": loss}
