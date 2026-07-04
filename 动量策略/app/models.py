from sqlalchemy import Column, Integer, String, Date, DECIMAL, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class Symbol(Base):
    __tablename__ = "symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    market = Column(String(20), nullable=False)
    category = Column(String(20), default="industry")
    data_source = Column(String(20), nullable=False)
    status = Column(Integer, default=1)
    min_volume = Column(Integer)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, nullable=False)
    trade_date = Column(Date, nullable=False)
    close_price = Column(DECIMAL(10, 4), nullable=False)
    open_price = Column(DECIMAL(10, 4))
    high_price = Column(DECIMAL(10, 4))
    low_price = Column(DECIMAL(10, 4))
    volume = Column(Integer)
    amount = Column(DECIMAL(18, 2))
    adjusted_factor = Column(DECIMAL(10, 6))
    is_suspended = Column(Integer, default=0)
    is_ex_dividend = Column(Integer, default=0)
    data_source = Column(String(20))
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol_id", "trade_date", name="uq_symbol_date"),
    )


class StrategyResult(Base):
    __tablename__ = "strategy_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol_id = Column(Integer, nullable=False)
    trade_date = Column(Date, nullable=False)
    momentum_20d = Column(DECIMAL(10, 4))
    volume_confirmed = Column(Integer, default=0)
    volume_change_pct = Column(DECIMAL(10, 4))
    ranking = Column(Integer)
    ranking_change = Column(Integer)
    trend_strength = Column(String(20))
    consecutive_days = Column(Integer, default=0)
    status = Column(String(20), default="valid")
    created_at = Column(TIMESTAMP, default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol_id", "trade_date", name="uq_result_symbol_date"),
    )
