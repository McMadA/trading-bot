"""Domain models as dataclasses with supporting enums."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


class PositionStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class Order:
    id: Optional[int]
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    status: OrderStatus
    filled_price: Optional[float]
    filled_at: Optional[datetime]
    fee: float
    created_at: datetime
    strategy_name: str


@dataclass
class Position:
    id: Optional[int]
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    current_price: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]
    unrealized_pnl: float
    realized_pnl: float
    status: PositionStatus
    opened_at: datetime
    closed_at: Optional[datetime]
    entry_order_id: int
    exit_order_id: Optional[int]


@dataclass
class PortfolioSnapshot:
    id: Optional[int]
    timestamp: datetime
    cash_balance: float
    positions_value: float
    total_value: float
    total_pnl: float
    total_pnl_pct: float


@dataclass
class TradeRecord:
    """A completed round-trip trade (entry + exit)."""
    id: Optional[int]
    symbol: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    fees: float
    strategy_name: str
    duration_minutes: int
