from __future__ import annotations

from pydantic import BaseModel, Field


class TradePlanBase(BaseModel):
    trade_date: str
    watch_symbols: list[str] = Field(default_factory=list)
    focus_sectors: list[str] = Field(default_factory=list)
    market_view: str = ""
    bull_case: str = ""
    bear_case: str = ""
    max_position: float = 0.0
    planned_trades: list[dict] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class TradePlanCreate(TradePlanBase):
    pass


class TradePlanOut(TradePlanBase):
    id: int


class DailyReviewBase(BaseModel):
    review_date: str
    status: str = "completed"
    market_score: float = 0.0
    market_environment: str = ""
    emotion_score: float = 0.0
    execution_score: float = 0.0
    discipline_score: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    largest_winner: str = ""
    largest_loser: str = ""
    mistakes: list[str] = Field(default_factory=list)
    good_decisions: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    tomorrow_plan: str = ""


class DailyReviewCreate(DailyReviewBase):
    pass


class DailyReviewOut(DailyReviewBase):
    id: int


class TradeLogBase(BaseModel):
    trade_date: str
    symbol: str
    action: str
    quantity: float = 0.0
    entry_price: float = 0.0
    exit_price: float = 0.0
    pnl: float = 0.0
    planned_trade: bool = False
    actual_reason: str = ""
    result_score: float = 0.0
    notes: str = ""


class TradeLogCreate(TradeLogBase):
    pass


class TradeLogOut(TradeLogBase):
    id: int


class AIReviewSummaryRequest(BaseModel):
    review_date: str


class AIReviewSummaryOut(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    repeated_mistakes: list[str]
    discipline_score: float
    risk_score: float
    suggestions: list[str]


class PlanDriftOut(BaseModel):
    discipline_score: float
    violations: list[dict]
    summary: str


class ReviewStatsOut(BaseModel):
    days: int
    win_rate: float
    average_pnl: float
    max_drawdown: float
    average_discipline_score: float
    consecutive_profit_days: int
    consecutive_loss_days: int
