"""Core trading engine — orchestrates data fetching, strategy execution, and order flow."""

import ccxt
import pandas as pd
import logging
import time
import threading
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from ..data.models import OrderType, OrderSide
from ..data.database import Database
from .portfolio import Portfolio
from .strategy import BaseStrategy, create_strategy

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Core trading engine. Coordinates data fetching, strategy execution,
    and order management via APScheduler.
    """

    def __init__(self, config, db: Database):
        self._config = config
        self._db = db
        self._running = False
        self._lock = threading.Lock()

        # CCXT exchange — public API only (no keys needed for Binance market data)
        exchange_name = config.get("exchange.name", "binance")
        self._exchange = getattr(ccxt, exchange_name)({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })

        # Virtual portfolio
        self._portfolio = Portfolio(
            initial_balance=config.get("trading.initial_balance", 10000.0),
            fee_rate=config.get("trading.fee_rate", 0.001),
            db=db,
            config=config,
        )

        # Active strategy
        self._strategy = create_strategy(config)

        # Trading pairs and timeframe
        self._pairs = config.get("trading.pairs", ["BTC/USDT"])
        self._timeframe = config.get("trading.default_timeframe", "15m")

        # Market data cache
        self._current_prices: dict[str, float] = {}
        self._ohlcv_data: dict[str, pd.DataFrame] = {}

        # APScheduler
        self._scheduler = BackgroundScheduler()

    def start(self):
        """Start the trading engine."""
        logger.info("Starting trading engine...")
        self._running = True

        # Initial data fetch
        self._tick()

        # Schedule periodic ticks
        interval = self._config.get("scheduler.interval_seconds", 60)
        self._scheduler.add_job(
            self._tick, "interval", seconds=interval, id="trading_tick",
            max_instances=1, coalesce=True,
        )
        self._scheduler.start()
        logger.info(
            f"Trading engine started. Strategy: {self._strategy.name}, "
            f"pairs: {self._pairs}, timeframe: {self._timeframe}, "
            f"interval: {interval}s"
        )

    def stop(self):
        """Stop the trading engine gracefully."""
        logger.info("Stopping trading engine...")
        self._running = False
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
        logger.info("Trading engine stopped.")

    def _tick(self):
        """One iteration of the trading loop."""
        if not self._running:
            return

        try:
            # 1. Fetch current prices and OHLCV data
            self._fetch_all_data()

            if not self._current_prices:
                logger.warning("No price data available, skipping tick")
                return

            # 2. Update portfolio positions with latest prices
            self._portfolio.update_positions(self._current_prices)

            # 3. Check pending limit/stop-loss orders
            self._portfolio.check_pending_orders(self._current_prices)

            # 4. Run strategy to generate signals
            current_positions = {
                symbol: self._portfolio.get_position(symbol)
                for symbol in self._pairs
            }
            signals = self._strategy.generate_signals(
                self._ohlcv_data, current_positions
            )

            # 5. Execute signals
            for signal in signals:
                self._execute_signal(signal)

            # 6. Take portfolio snapshot
            self._portfolio.take_snapshot(self._current_prices)

        except Exception as e:
            logger.error(f"Error in trading tick: {e}", exc_info=True)

    def _fetch_all_data(self):
        """Fetch OHLCV data for all configured pairs."""
        for symbol in self._pairs:
            df = self._fetch_ohlcv(symbol, self._timeframe)
            if df is not None:
                self._ohlcv_data[symbol] = df
                self._current_prices[symbol] = float(df.iloc[-1]["close"])

    def _fetch_ohlcv(self, symbol: str, timeframe: str,
                     limit: int = 100, retries: int = 3,
                     delay: float = 5.0) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data with retry logic (adapted from v1 pattern)."""
        for attempt in range(retries):
            try:
                candles = self._exchange.fetch_ohlcv(
                    symbol, timeframe, limit=limit
                )
                if not candles:
                    logger.warning(f"No data received for {symbol}")
                    return None

                df = pd.DataFrame(candles, columns=[
                    "timestamp", "open", "high", "low", "close", "volume"
                ])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                return df

            except ccxt.NetworkError as e:
                logger.warning(f"Network error fetching {symbol}: {e}")
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error fetching {symbol}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching {symbol}: {e}")

            if attempt < retries - 1:
                time.sleep(delay)

        logger.error(f"Max retries reached fetching {symbol}")
        return None

    def _execute_signal(self, signal):
        """Convert a Signal into an Order and submit to portfolio."""
        current_price = self._current_prices.get(signal.symbol)
        if current_price is None:
            return

        quantity = self._portfolio.calculate_position_size(
            signal.symbol, signal.side, current_price
        )

        if quantity <= 0:
            logger.info(f"Skipping signal for {signal.symbol}: "
                        f"insufficient size or max positions reached")
            return

        logger.info(
            f"Executing {signal.side.value} signal for {signal.symbol}: "
            f"qty={quantity:.6f}, price={current_price:.4f}, "
            f"reason={signal.reason}"
        )

        order = self._portfolio.submit_order(
            symbol=signal.symbol,
            side=signal.side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=current_price,
            strategy_name=self._strategy.name,
        )

        # Set stop-loss and take-profit on new buy positions
        if signal.side == OrderSide.BUY and order and order.status.value == "filled":
            sl_pct = self._config.get("risk_management.stop_loss_pct", 0.03)
            tp_pct = self._config.get("risk_management.take_profit_pct", 0.06)
            position = self._portfolio.get_position(signal.symbol)
            if position:
                position.stop_loss_price = current_price * (1 - sl_pct)
                position.take_profit_price = current_price * (1 + tp_pct)
                self._db.update_position(position)
                logger.info(
                    f"Set SL={position.stop_loss_price:.4f}, "
                    f"TP={position.take_profit_price:.4f} for {signal.symbol}"
                )

    # --- Public accessors for dashboard ---

    @property
    def portfolio(self) -> Portfolio:
        return self._portfolio

    @property
    def strategy(self) -> BaseStrategy:
        return self._strategy

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def current_prices(self) -> dict[str, float]:
        return dict(self._current_prices)

    @property
    def ohlcv_data(self) -> dict[str, pd.DataFrame]:
        return dict(self._ohlcv_data)

    def get_pair_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get OHLCV data with indicators computed (for charting)."""
        df = self._ohlcv_data.get(symbol)
        if df is not None:
            df = self._strategy.calculate_indicators(df.copy())
        return df

    def change_strategy(self, strategy_name: str, params: dict = None):
        """Hot-swap the active strategy."""
        with self._lock:
            if "strategy" not in self._config._data:
                self._config._data["strategy"] = {}
            self._config._data["strategy"]["active"] = strategy_name
            if params:
                self._config._data["strategy"][strategy_name] = params
            self._strategy = create_strategy(self._config)
            logger.info(f"Strategy changed to {strategy_name}")
