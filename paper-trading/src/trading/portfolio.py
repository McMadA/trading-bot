"""Virtual portfolio manager — acts as the simulated exchange."""

import logging
import threading
from datetime import datetime
from typing import Optional

from ..data.models import (
    Order, Position, PortfolioSnapshot, TradeRecord,
    OrderSide, OrderType, OrderStatus, PositionStatus,
)
from ..data.database import Database

logger = logging.getLogger(__name__)


class Portfolio:
    """
    Virtual portfolio that simulates exchange order execution.
    All paper-trade orders go through this class instead of the real exchange.
    Thread-safe: the engine thread writes, Flask threads read.
    """

    def __init__(self, initial_balance: float, fee_rate: float,
                 db: Database, config):
        self._initial_balance = initial_balance
        self._cash_balance = initial_balance
        self._fee_rate = fee_rate
        self._db = db
        self._config = config
        self._positions: dict[str, Position] = {}  # symbol -> Position
        self._pending_orders: list[Order] = []
        self._lock = threading.RLock()
        self._restore_state()

    def _restore_state(self):
        """Reload open positions and pending orders from DB on restart."""
        open_positions = self._db.get_open_positions()
        for pos in open_positions:
            self._positions[pos.symbol] = pos

        pending = self._db.get_pending_orders()
        self._pending_orders = pending

        # Recalculate cash: initial - cost of open positions
        total_invested = sum(
            p.entry_price * p.quantity for p in open_positions
        )
        total_fees = sum(
            p.entry_price * p.quantity * self._fee_rate for p in open_positions
        )
        self._cash_balance = self._initial_balance - total_invested - total_fees

        if open_positions:
            logger.info(
                f"Restored {len(open_positions)} open positions, "
                f"cash balance: {self._cash_balance:.2f}"
            )

    # --- Order submission ---

    def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                     quantity: float, price: float = None,
                     stop_price: float = None,
                     strategy_name: str = "") -> Optional[Order]:
        with self._lock:
            now = datetime.now()
            order = Order(
                id=None,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status=OrderStatus.PENDING,
                filled_price=None,
                filled_at=None,
                fee=0.0,
                created_at=now,
                strategy_name=strategy_name,
            )

            order.id = self._db.insert_order(order)

            if order_type == OrderType.MARKET:
                if price is None:
                    logger.warning(f"Market order for {symbol} has no price")
                    return None
                return self._execute_fill(order, price)
            else:
                self._pending_orders.append(order)
                logger.info(
                    f"Pending {order_type.value} order #{order.id}: "
                    f"{side.value} {quantity} {symbol} @ {price or stop_price}"
                )
                return order

    def _execute_fill(self, order: Order, fill_price: float) -> Order:
        """Fill an order at the given price."""
        fee = fill_price * order.quantity * self._fee_rate
        order.filled_price = fill_price
        order.filled_at = datetime.now()
        order.fee = fee
        order.status = OrderStatus.FILLED

        self._db.update_order_status(
            order.id, OrderStatus.FILLED, fill_price, order.filled_at
        )

        if order.side == OrderSide.BUY:
            cost = fill_price * order.quantity + fee
            if cost > self._cash_balance:
                logger.warning(
                    f"Insufficient cash for {order.symbol}: "
                    f"need {cost:.2f}, have {self._cash_balance:.2f}"
                )
                order.status = OrderStatus.CANCELLED
                self._db.update_order_status(order.id, OrderStatus.CANCELLED)
                return order

            self._cash_balance -= cost
            self._open_position(order, fill_price)
            logger.info(
                f"BUY filled #{order.id}: {order.quantity} {order.symbol} "
                f"@ {fill_price:.4f}, fee={fee:.4f}, cash={self._cash_balance:.2f}"
            )

        elif order.side == OrderSide.SELL:
            position = self._positions.get(order.symbol)
            if position is None:
                logger.warning(f"No open position to sell for {order.symbol}")
                order.status = OrderStatus.CANCELLED
                self._db.update_order_status(order.id, OrderStatus.CANCELLED)
                return order

            proceeds = fill_price * order.quantity - fee
            self._cash_balance += proceeds
            self._close_position(position, order, fill_price, fee)
            logger.info(
                f"SELL filled #{order.id}: {order.quantity} {order.symbol} "
                f"@ {fill_price:.4f}, fee={fee:.4f}, cash={self._cash_balance:.2f}"
            )

        return order

    def _open_position(self, order: Order, fill_price: float):
        """Create a new position from a filled buy order."""
        position = Position(
            id=None,
            symbol=order.symbol,
            side=OrderSide.BUY,
            quantity=order.quantity,
            entry_price=fill_price,
            current_price=fill_price,
            stop_loss_price=None,
            take_profit_price=None,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            status=PositionStatus.OPEN,
            opened_at=datetime.now(),
            closed_at=None,
            entry_order_id=order.id,
            exit_order_id=None,
        )
        position.id = self._db.insert_position(position)
        self._positions[order.symbol] = position

    def _close_position(self, position: Position, exit_order: Order,
                        exit_price: float, exit_fee: float):
        """Close a position and record the trade."""
        entry_fee = position.entry_price * position.quantity * self._fee_rate
        pnl = (exit_price - position.entry_price) * position.quantity - entry_fee - exit_fee
        pnl_pct = ((exit_price / position.entry_price) - 1) * 100 if position.entry_price > 0 else 0.0

        now = datetime.now()
        duration = int((now - position.opened_at).total_seconds() / 60)

        record = TradeRecord(
            id=None,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            entry_time=position.opened_at,
            exit_time=now,
            pnl=pnl,
            pnl_pct=pnl_pct,
            fees=entry_fee + exit_fee,
            strategy_name=exit_order.strategy_name,
            duration_minutes=duration,
        )
        self._db.insert_trade_record(record)

        position.status = PositionStatus.CLOSED
        position.closed_at = now
        position.exit_order_id = exit_order.id
        position.realized_pnl = pnl
        position.unrealized_pnl = 0.0
        position.current_price = exit_price
        self._db.update_position(position)

        del self._positions[position.symbol]

    # --- Position sizing ---

    def calculate_position_size(self, symbol: str, side: OrderSide,
                                current_price: float) -> float:
        """Calculate quantity based on risk management rules."""
        if side == OrderSide.SELL:
            position = self._positions.get(symbol)
            return position.quantity if position else 0.0

        max_pct = self._config.get("risk_management.max_position_pct", 0.25)
        max_positions = self._config.get("risk_management.max_open_positions", 4)

        if len(self._positions) >= max_positions:
            return 0.0

        total_value = self._cash_balance + sum(
            p.current_price * p.quantity for p in self._positions.values()
        )
        max_cost = total_value * max_pct
        available = min(max_cost, self._cash_balance)

        # Account for fees
        available_after_fee = available / (1 + self._fee_rate)
        quantity = available_after_fee / current_price if current_price > 0 else 0.0

        return quantity

    # --- Pending order management ---

    def check_pending_orders(self, current_prices: dict[str, float]):
        """Check if any pending limit or stop-loss orders should trigger."""
        with self._lock:
            triggered = []
            remaining = []

            for order in self._pending_orders:
                price = current_prices.get(order.symbol)
                if price is None:
                    remaining.append(order)
                    continue

                should_fill = False
                if order.order_type == OrderType.LIMIT:
                    if order.side == OrderSide.BUY and price <= order.price:
                        should_fill = True
                    elif order.side == OrderSide.SELL and price >= order.price:
                        should_fill = True
                elif order.order_type == OrderType.STOP_LOSS:
                    if order.stop_price and price <= order.stop_price:
                        should_fill = True

                if should_fill:
                    triggered.append((order, price))
                else:
                    remaining.append(order)

            self._pending_orders = remaining

            for order, price in triggered:
                logger.info(
                    f"Pending order #{order.id} triggered at {price:.4f}"
                )
                self._execute_fill(order, price)

    # --- Position updates ---

    def update_positions(self, current_prices: dict[str, float]):
        """Update current prices and unrealized P&L for all open positions."""
        with self._lock:
            for symbol, position in list(self._positions.items()):
                price = current_prices.get(symbol)
                if price is None:
                    continue

                position.current_price = price
                position.unrealized_pnl = (
                    (price - position.entry_price) * position.quantity
                )
                self._db.update_position(position)

                self._check_stop_loss_take_profit(position, price)

    def _check_stop_loss_take_profit(self, position: Position, current_price: float):
        """Auto-close position if SL or TP is hit."""
        if position.stop_loss_price and current_price <= position.stop_loss_price:
            logger.info(
                f"Stop-loss triggered for {position.symbol} "
                f"at {current_price:.4f} (SL={position.stop_loss_price:.4f})"
            )
            self._auto_close(position, current_price, "stop_loss")

        elif position.take_profit_price and current_price >= position.take_profit_price:
            logger.info(
                f"Take-profit triggered for {position.symbol} "
                f"at {current_price:.4f} (TP={position.take_profit_price:.4f})"
            )
            self._auto_close(position, current_price, "take_profit")

    def _auto_close(self, position: Position, price: float, reason: str):
        """Create a sell order to close a position automatically."""
        order = Order(
            id=None,
            symbol=position.symbol,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=position.quantity,
            price=price,
            stop_price=None,
            status=OrderStatus.PENDING,
            filled_price=None,
            filled_at=None,
            fee=0.0,
            created_at=datetime.now(),
            strategy_name=f"auto_{reason}",
        )
        order.id = self._db.insert_order(order)
        self._execute_fill(order, price)

    def cancel_order(self, order_id: int):
        with self._lock:
            self._pending_orders = [
                o for o in self._pending_orders if o.id != order_id
            ]
            self._db.update_order_status(order_id, OrderStatus.CANCELLED)

    # --- Portfolio state ---

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def get_all_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_cash_balance(self) -> float:
        return self._cash_balance

    def get_total_value(self, current_prices: dict[str, float]) -> float:
        return self._cash_balance + self.get_positions_value(current_prices)

    def get_positions_value(self, current_prices: dict[str, float]) -> float:
        total = 0.0
        for symbol, pos in self._positions.items():
            price = current_prices.get(symbol, pos.current_price)
            total += price * pos.quantity
        return total

    def take_snapshot(self, current_prices: dict[str, float]):
        """Create and persist a portfolio snapshot."""
        positions_value = self.get_positions_value(current_prices)
        total_value = self._cash_balance + positions_value
        total_pnl = total_value - self._initial_balance
        total_pnl_pct = (total_pnl / self._initial_balance * 100) if self._initial_balance > 0 else 0.0

        snapshot = PortfolioSnapshot(
            id=None,
            timestamp=datetime.now(),
            cash_balance=self._cash_balance,
            positions_value=positions_value,
            total_value=total_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
        )
        self._db.insert_snapshot(snapshot)

    def get_portfolio_summary(self, current_prices: dict[str, float]) -> dict:
        positions_value = self.get_positions_value(current_prices)
        total_value = self._cash_balance + positions_value
        total_pnl = total_value - self._initial_balance
        total_pnl_pct = (total_pnl / self._initial_balance * 100) if self._initial_balance > 0 else 0.0

        return {
            "initial_balance": self._initial_balance,
            "cash_balance": round(self._cash_balance, 2),
            "positions_value": round(positions_value, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "open_positions": len(self._positions),
        }

    def get_trade_history(self, limit=100) -> list[TradeRecord]:
        return self._db.get_trade_records(limit=limit)

    def get_performance_stats(self) -> dict:
        return self._db.get_performance_stats()
