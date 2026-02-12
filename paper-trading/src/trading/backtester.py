"""Walk-forward backtester using the same Strategy and Portfolio classes as live trading."""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import ccxt
import pandas as pd

from ..data.models import OrderType, OrderSide, TradeRecord
from ..data.database import Database
from .portfolio import Portfolio
from .strategy import BaseStrategy, EMASMACrossoverStrategy, RSIStrategy, CombinedStrategy

logger = logging.getLogger(__name__)


class BacktestResult:
    """Container for backtesting results."""

    def __init__(self):
        self.trades: list[TradeRecord] = []
        self.equity_curve: list[dict] = []
        self.total_return_pct: float = 0.0
        self.win_rate: float = 0.0
        self.max_drawdown_pct: float = 0.0
        self.total_trades: int = 0
        self.avg_trade_pnl: float = 0.0


class Backtester:
    """
    Runs a strategy against historical OHLCV data.
    Uses the same Strategy classes and Portfolio logic as live trading.
    """

    def __init__(self, config, exchange):
        self._config = config
        self._exchange = exchange

    def run(self, strategy_name: str, strategy_params: dict,
            symbols: list[str], timeframe: str, days: int = 30,
            initial_balance: float = 10000.0) -> BacktestResult:
        """Execute a full backtest."""
        logger.info(
            f"Starting backtest: strategy={strategy_name}, "
            f"symbols={symbols}, timeframe={timeframe}, days={days}"
        )

        # Create strategy instance
        strategy = self._create_strategy(strategy_name, strategy_params)

        # Fetch historical data for all symbols
        historical_data = {}
        for symbol in symbols:
            df = self._fetch_historical_data(symbol, timeframe, days)
            if df is not None and len(df) > 0:
                historical_data[symbol] = df

        if not historical_data:
            logger.warning("No historical data available for backtest")
            result = BacktestResult()
            return result

        # Create temporary in-memory database and portfolio
        db = Database(":memory:")
        portfolio = Portfolio(
            initial_balance=initial_balance,
            fee_rate=self._config.get("trading.fee_rate", 0.001),
            db=db,
            config=self._config,
        )

        # Determine the common index range
        min_len = min(len(df) for df in historical_data.values())
        warmup = max(
            strategy_params.get("ema_period", 20),
            strategy_params.get("sma_period", 20),
            strategy_params.get("period", 14),
            strategy_params.get("rsi_period", 14),
        ) + 5  # Extra padding for indicator warmup

        if min_len <= warmup:
            logger.warning("Not enough data for warmup period")
            return BacktestResult()

        # Walk-forward simulation
        snapshots = []
        for i in range(warmup, min_len):
            # Build data windows up to current candle
            windows = {}
            current_prices = {}
            for symbol, df in historical_data.items():
                window = df.iloc[: i + 1]
                windows[symbol] = window
                current_prices[symbol] = float(window.iloc[-1]["close"])

            # Update portfolio positions
            portfolio.update_positions(current_prices)
            portfolio.check_pending_orders(current_prices)

            # Run strategy
            current_positions = {
                symbol: portfolio.get_position(symbol)
                for symbol in symbols
            }
            signals = strategy.generate_signals(windows, current_positions)

            # Execute signals
            for signal in signals:
                price = current_prices.get(signal.symbol)
                if price is None:
                    continue

                quantity = portfolio.calculate_position_size(
                    signal.symbol, signal.side, price
                )
                if quantity <= 0:
                    continue

                order = portfolio.submit_order(
                    symbol=signal.symbol,
                    side=signal.side,
                    order_type=OrderType.MARKET,
                    quantity=quantity,
                    price=price,
                    strategy_name=strategy.name,
                )

                # Set SL/TP for buy orders
                if (signal.side == OrderSide.BUY and order
                        and order.status.value == "filled"):
                    sl_pct = self._config.get("risk_management.stop_loss_pct", 0.03)
                    tp_pct = self._config.get("risk_management.take_profit_pct", 0.06)
                    position = portfolio.get_position(signal.symbol)
                    if position:
                        position.stop_loss_price = price * (1 - sl_pct)
                        position.take_profit_price = price * (1 + tp_pct)
                        db.update_position(position)

            # Record snapshot
            total_value = portfolio.get_total_value(current_prices)
            timestamp = historical_data[symbols[0]].iloc[i]["timestamp"]
            snapshots.append({
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
                "value": total_value,
            })

        # Compile results
        result = BacktestResult()
        result.equity_curve = snapshots
        result.trades = db.get_trade_records(limit=10000)
        result.total_trades = len(result.trades)

        if result.total_trades > 0:
            winning = sum(1 for t in result.trades if t.pnl > 0)
            result.win_rate = (winning / result.total_trades) * 100
            result.avg_trade_pnl = sum(t.pnl for t in result.trades) / result.total_trades
        else:
            result.win_rate = 0.0
            result.avg_trade_pnl = 0.0

        # Calculate total return
        if snapshots:
            final_value = snapshots[-1]["value"]
            result.total_return_pct = ((final_value / initial_balance) - 1) * 100

        # Calculate max drawdown
        result.max_drawdown_pct = self._calculate_max_drawdown(snapshots)

        logger.info(
            f"Backtest complete: {result.total_trades} trades, "
            f"return={result.total_return_pct:.2f}%, "
            f"win_rate={result.win_rate:.1f}%, "
            f"max_drawdown={result.max_drawdown_pct:.2f}%"
        )

        return result

    def _create_strategy(self, name: str, params: dict) -> BaseStrategy:
        strategies = {
            "ema_sma_crossover": EMASMACrossoverStrategy,
            "rsi": RSIStrategy,
            "combined": CombinedStrategy,
        }
        cls = strategies.get(name)
        if cls is None:
            raise ValueError(f"Unknown strategy: {name}")
        return cls(params)

    def _fetch_historical_data(self, symbol: str, timeframe: str,
                                days: int) -> Optional[pd.DataFrame]:
        """Fetch historical OHLCV data, paginating if necessary."""
        logger.info(f"Fetching {days} days of {timeframe} data for {symbol}")

        # Calculate how many candles we need
        tf_minutes = self._timeframe_to_minutes(timeframe)
        total_candles = (days * 24 * 60) // tf_minutes
        limit_per_request = 1000

        all_candles = []
        since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        while len(all_candles) < total_candles:
            try:
                candles = self._exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=limit_per_request
                )
                if not candles:
                    break

                all_candles.extend(candles)
                # Move since to after the last candle
                since = candles[-1][0] + 1

                if len(candles) < limit_per_request:
                    break  # No more data available

                time.sleep(self._exchange.rateLimit / 1000)

            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                logger.warning(f"Error fetching historical data for {symbol}: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error fetching {symbol}: {e}")
                break

        if not all_candles:
            return None

        df = pd.DataFrame(all_candles, columns=[
            "timestamp", "open", "high", "low", "close", "volume"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        logger.info(f"Fetched {len(df)} candles for {symbol}")
        return df

    @staticmethod
    def _timeframe_to_minutes(timeframe: str) -> int:
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        multipliers = {"m": 1, "h": 60, "d": 1440, "w": 10080}
        return value * multipliers.get(unit, 1)

    @staticmethod
    def _calculate_max_drawdown(snapshots: list[dict]) -> float:
        if not snapshots:
            return 0.0

        peak = snapshots[0]["value"]
        max_dd = 0.0

        for s in snapshots:
            value = s["value"]
            if value > peak:
                peak = value
            dd = ((peak - value) / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        return max_dd
