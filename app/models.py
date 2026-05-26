"""SQLAlchemy ORM models."""
from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint, Text
from sqlalchemy.sql import func

from app.database import Base


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"
    __table_args__ = (UniqueConstraint("code", "timestamp", name="uq_code_timestamp"),)
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False, default=0.0)
    pct_change = Column(Float, nullable=False, default=0.0)
    change = Column(Float, nullable=False, default=0.0)
    volume = Column(Float, nullable=False, default=0.0)
    amount = Column(Float, nullable=False, default=0.0)
    turnover_rate = Column(Float, nullable=False, default=0.0)
    pe = Column(Float, nullable=False, default=0.0)
    pb = Column(Float, nullable=False, default=0.0)
    total_market_cap = Column(Float, nullable=False, default=0.0)
    float_market_cap = Column(Float, nullable=False, default=0.0)
    timestamp = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DailyBar(Base):
    __tablename__ = "daily_bars"
    __table_args__ = (UniqueConstraint("code", "trade_date", name="uq_daily_code_trade_date"),)
    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    trade_date = Column(String(16), nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    pct_change = Column(Float)
    turnover_rate = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class StockSignal(Base):
    __tablename__ = "stock_signals"
    __table_args__ = (UniqueConstraint("code", "trade_date", "signal_name", name="uq_signal_code_date_name"),)
    id = Column(Integer, primary_key=True)
    code = Column(String(20), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    trade_date = Column(String(16), index=True, nullable=False)
    signal_name = Column(String(64), nullable=False)
    signal_type = Column(String(20), nullable=False)
    strength = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    generated_at = Column(String(32), nullable=False)


class StockScore(Base):
    __tablename__ = "stock_scores"
    __table_args__ = (UniqueConstraint("code", "trade_date", name="uq_score_code_trade_date"),)
    id = Column(Integer, primary_key=True)
    code = Column(String(20), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    trade_date = Column(String(16), index=True, nullable=False)
    total_score = Column(Float, nullable=False)
    trend_score = Column(Float, nullable=False)
    momentum_score = Column(Float, nullable=False)
    relative_strength_score = Column(Float, nullable=False)
    liquidity_score = Column(Float, nullable=False)
    position_score = Column(Float, nullable=False)
    risk_penalty = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    reasons = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class NewsAnalysis(Base):
    __tablename__ = "news_analysis"
    __table_args__ = (UniqueConstraint("stock_code", "analysis_date", name="uq_news_code_date"),)
    id = Column(Integer, primary_key=True)
    stock_code = Column(String(20), index=True, nullable=False)
    analysis_date = Column(String(16), index=True, nullable=False)
    raw_analysis = Column(Text, nullable=True)
    ai_sentiment_score = Column(Float, nullable=False, default=50.0)
    ai_confidence = Column(Float, nullable=False, default=0.0)
    ai_policy_boost = Column(Float, nullable=False, default=0.0)
    ai_fundamental_boost = Column(Float, nullable=False, default=0.0)
    ai_reasons = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id = Column(Integer, primary_key=True)
    test_type = Column(String(50), index=True, nullable=False)
    trade_date = Column(String(16), index=True, nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
