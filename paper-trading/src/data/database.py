"""SQLite database layer for persisting trades, positions, and portfolio history."""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

from .models import (
    Order, Position, PortfolioSnapshot, TradeRecord,
    OrderSide, OrderType, OrderStatus, PositionStatus,
)


class Database:
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._write_lock = threading.Lock()
        self._init_tables()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL,
                    stop_price REAL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    filled_price REAL,
                    filled_at TEXT,
                    fee REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    strategy_name TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    stop_loss_price REAL,
                    take_profit_price REAL,
                    unrealized_pnl REAL NOT NULL DEFAULT 0,
                    realized_pnl REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'open',
                    opened_at TEXT NOT NULL,
                    closed_at TEXT,
                    entry_order_id INTEGER NOT NULL,
                    exit_order_id INTEGER
                );

                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cash_balance REAL NOT NULL,
                    positions_value REAL NOT NULL,
                    total_value REAL NOT NULL,
                    total_pnl REAL NOT NULL,
                    total_pnl_pct REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS trade_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_pct REAL NOT NULL,
                    fees REAL NOT NULL,
                    strategy_name TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_orders_symbol_status ON orders(symbol, status);
                CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON portfolio_snapshots(timestamp);
                CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trade_records(symbol);
            """)

    # --- Order operations ---

    def insert_order(self, order: Order) -> int:
        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO orders
                       (symbol, side, order_type, quantity, price, stop_price,
                        status, filled_price, filled_at, fee, created_at, strategy_name)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        order.symbol, order.side.value, order.order_type.value,
                        order.quantity, order.price, order.stop_price,
                        order.status.value,
                        order.filled_price,
                        order.filled_at.isoformat() if order.filled_at else None,
                        order.fee,
                        order.created_at.isoformat(),
                        order.strategy_name,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def update_order_status(self, order_id: int, status: OrderStatus,
                            filled_price: float = None, filled_at: datetime = None):
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE orders SET status=?, filled_price=?, filled_at=?
                       WHERE id=?""",
                    (
                        status.value, filled_price,
                        filled_at.isoformat() if filled_at else None,
                        order_id,
                    ),
                )
                conn.commit()

    def get_pending_orders(self, symbol: str = None) -> list[Order]:
        with self._get_connection() as conn:
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE status='pending' AND symbol=? ORDER BY created_at",
                    (symbol,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE status='pending' ORDER BY created_at"
                ).fetchall()
        return [self._row_to_order(r) for r in rows]

    def get_orders(self, symbol: str = None, limit: int = 100) -> list[Order]:
        with self._get_connection() as conn:
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
                    (symbol, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_order(r) for r in rows]

    # --- Position operations ---

    def insert_position(self, position: Position) -> int:
        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO positions
                       (symbol, side, quantity, entry_price, current_price,
                        stop_loss_price, take_profit_price, unrealized_pnl,
                        realized_pnl, status, opened_at, closed_at,
                        entry_order_id, exit_order_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        position.symbol, position.side.value, position.quantity,
                        position.entry_price, position.current_price,
                        position.stop_loss_price, position.take_profit_price,
                        position.unrealized_pnl, position.realized_pnl,
                        position.status.value, position.opened_at.isoformat(),
                        position.closed_at.isoformat() if position.closed_at else None,
                        position.entry_order_id, position.exit_order_id,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def update_position(self, position: Position):
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE positions SET
                       current_price=?, stop_loss_price=?, take_profit_price=?,
                       unrealized_pnl=?, realized_pnl=?, status=?, closed_at=?,
                       exit_order_id=?
                       WHERE id=?""",
                    (
                        position.current_price, position.stop_loss_price,
                        position.take_profit_price, position.unrealized_pnl,
                        position.realized_pnl, position.status.value,
                        position.closed_at.isoformat() if position.closed_at else None,
                        position.exit_order_id, position.id,
                    ),
                )
                conn.commit()

    def update_positions_batch(self, positions: list[Position]):
        if not positions:
            return
        with self._write_lock:
            with self._get_connection() as conn:
                conn.executemany(
                    """UPDATE positions SET
                       current_price=?, stop_loss_price=?, take_profit_price=?,
                       unrealized_pnl=?, realized_pnl=?, status=?, closed_at=?,
                       exit_order_id=?
                       WHERE id=?""",
                    [
                        (
                            p.current_price, p.stop_loss_price,
                            p.take_profit_price, p.unrealized_pnl,
                            p.realized_pnl, p.status.value,
                            p.closed_at.isoformat() if p.closed_at else None,
                            p.exit_order_id, p.id,
                        )
                        for p in positions
                    ],
                )
                conn.commit()

    def get_open_positions(self) -> list[Position]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status='open' ORDER BY opened_at"
            ).fetchall()
        return [self._row_to_position(r) for r in rows]

    def close_position(self, position_id: int, exit_price: float,
                       exit_order_id: int, realized_pnl: float):
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE positions SET status='closed', current_price=?,
                       closed_at=?, exit_order_id=?, realized_pnl=?, unrealized_pnl=0
                       WHERE id=?""",
                    (exit_price, datetime.now().isoformat(), exit_order_id,
                     realized_pnl, position_id),
                )
                conn.commit()

    # --- Portfolio snapshots ---

    def insert_snapshot(self, snapshot: PortfolioSnapshot):
        with self._write_lock:
            with self._get_connection() as conn:
                conn.execute(
                    """INSERT INTO portfolio_snapshots
                       (timestamp, cash_balance, positions_value, total_value,
                        total_pnl, total_pnl_pct)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        snapshot.timestamp.isoformat(),
                        snapshot.cash_balance, snapshot.positions_value,
                        snapshot.total_value, snapshot.total_pnl, snapshot.total_pnl_pct,
                    ),
                )
                conn.commit()

    def get_snapshots(self, hours: int = 24) -> list[PortfolioSnapshot]:
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolio_snapshots WHERE timestamp >= ? ORDER BY timestamp",
                (since,),
            ).fetchall()
        return [self._row_to_snapshot(r) for r in rows]

    def get_latest_snapshot(self) -> Optional[PortfolioSnapshot]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        return self._row_to_snapshot(row) if row else None

    # --- Trade records ---

    def insert_trade_record(self, record: TradeRecord) -> int:
        with self._write_lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """INSERT INTO trade_records
                       (symbol, side, entry_price, exit_price, quantity,
                        entry_time, exit_time, pnl, pnl_pct, fees,
                        strategy_name, duration_minutes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.symbol, record.side.value, record.entry_price,
                        record.exit_price, record.quantity,
                        record.entry_time.isoformat(), record.exit_time.isoformat(),
                        record.pnl, record.pnl_pct, record.fees,
                        record.strategy_name, record.duration_minutes,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def get_trade_records(self, symbol: str = None, limit: int = 100) -> list[TradeRecord]:
        with self._get_connection() as conn:
            if symbol:
                rows = conn.execute(
                    "SELECT * FROM trade_records WHERE symbol=? ORDER BY exit_time DESC LIMIT ?",
                    (symbol, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trade_records ORDER BY exit_time DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_trade_record(r) for r in rows]

    def get_performance_stats(self) -> dict:
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*) as total_trades,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                       AVG(pnl) as avg_pnl,
                       MAX(pnl) as best_trade,
                       MIN(pnl) as worst_trade,
                       SUM(pnl) as total_pnl,
                       SUM(fees) as total_fees
                   FROM trade_records"""
            ).fetchone()

        total = row["total_trades"] or 0
        winning = row["winning_trades"] or 0

        return {
            "total_trades": total,
            "winning_trades": winning,
            "win_rate": (winning / total * 100) if total > 0 else 0.0,
            "avg_pnl": row["avg_pnl"] or 0.0,
            "best_trade": row["best_trade"] or 0.0,
            "worst_trade": row["worst_trade"] or 0.0,
            "total_pnl": row["total_pnl"] or 0.0,
            "total_fees": row["total_fees"] or 0.0,
        }

    # --- Row-to-model converters ---

    @staticmethod
    def _row_to_order(row) -> Order:
        return Order(
            id=row["id"],
            symbol=row["symbol"],
            side=OrderSide(row["side"]),
            order_type=OrderType(row["order_type"]),
            quantity=row["quantity"],
            price=row["price"],
            stop_price=row["stop_price"],
            status=OrderStatus(row["status"]),
            filled_price=row["filled_price"],
            filled_at=datetime.fromisoformat(row["filled_at"]) if row["filled_at"] else None,
            fee=row["fee"],
            created_at=datetime.fromisoformat(row["created_at"]),
            strategy_name=row["strategy_name"],
        )

    @staticmethod
    def _row_to_position(row) -> Position:
        return Position(
            id=row["id"],
            symbol=row["symbol"],
            side=OrderSide(row["side"]),
            quantity=row["quantity"],
            entry_price=row["entry_price"],
            current_price=row["current_price"],
            stop_loss_price=row["stop_loss_price"],
            take_profit_price=row["take_profit_price"],
            unrealized_pnl=row["unrealized_pnl"],
            realized_pnl=row["realized_pnl"],
            status=PositionStatus(row["status"]),
            opened_at=datetime.fromisoformat(row["opened_at"]),
            closed_at=datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None,
            entry_order_id=row["entry_order_id"],
            exit_order_id=row["exit_order_id"],
        )

    @staticmethod
    def _row_to_snapshot(row) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            cash_balance=row["cash_balance"],
            positions_value=row["positions_value"],
            total_value=row["total_value"],
            total_pnl=row["total_pnl"],
            total_pnl_pct=row["total_pnl_pct"],
        )

    @staticmethod
    def _row_to_trade_record(row) -> TradeRecord:
        return TradeRecord(
            id=row["id"],
            symbol=row["symbol"],
            side=OrderSide(row["side"]),
            entry_price=row["entry_price"],
            exit_price=row["exit_price"],
            quantity=row["quantity"],
            entry_time=datetime.fromisoformat(row["entry_time"]),
            exit_time=datetime.fromisoformat(row["exit_time"]),
            pnl=row["pnl"],
            pnl_pct=row["pnl_pct"],
            fees=row["fees"],
            strategy_name=row["strategy_name"],
            duration_minutes=row["duration_minutes"],
        )
