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
from .strategy import (
    BaseStrategy, EMASMACrossoverStrategy, RSIStrategy, CombinedStrategy,
    DEFAULT_EMA_PERIOD, DEFAULT_SMA_PERIOD, DEFAULT_RSI_PERIOD
)

logger = logging.getLogger(__name__)

# Default Simulation Parameters
DEFAULT_INITIAL_BALANCE = 10000.0
DEFAULT_BACKTEST_DAYS = 30
DEFAULT_FEE_RATE = 0.001
DEFAULT_STOP_LOSS_PCT = 0.03
DEFAULT_TAKE_PROFIT_PCT = 0.06


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
        # Metadata for comparison
        self.strategy_name: str = ""
        self.strategy_params: dict = {}
        self.initial_balance: float = DEFAULT_INITIAL_BALANCE
        self.stop_loss_pct: float = 0.0
        self.take_profit_pct: float = 0.0


def _create_strategy(name: str, params: dict) -> BaseStrategy:
    strategies = {
        "ema_sma_crossover": EMASMACrossoverStrategy,
        "rsi": RSIStrategy,
        "combined": CombinedStrategy,
    }
    cls = strategies.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}")
    return cls(params)


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


def run_backtest_simulation(config: dict, strategy_name: str, strategy_params: dict,
                            symbols: list[str], timeframe: str, days: int,
                            initial_balance: float, stop_loss_pct: float,
                            take_profit_pct: float, historical_data: dict,
                            progress_callback=None, log_results=True) -> BacktestResult:
    """Execute a full backtest simulation independently of Backtester instance."""

    # Resolve SL/TP values
    sl_pct = stop_loss_pct if stop_loss_pct is not None else config.get("risk_management.stop_loss_pct", DEFAULT_STOP_LOSS_PCT)
    tp_pct = take_profit_pct if take_profit_pct is not None else config.get("risk_management.take_profit_pct", DEFAULT_TAKE_PROFIT_PCT)

    # Create strategy instance
    strategy = _create_strategy(strategy_name, strategy_params)

    if not historical_data:
        logger.warning("No historical data available for backtest")
        result = BacktestResult()
        return result

    # Clone historical_data so we don't modify the caller's reference
    historical_data = historical_data.copy()

    # Create temporary in-memory database and portfolio
    db = Database(":memory:")
    portfolio = Portfolio(
        initial_balance=initial_balance,
        fee_rate=config.get("trading.fee_rate", DEFAULT_FEE_RATE),
        db=db,
        config=config,
    )

    # Pre-calculate indicators for all symbols
    for symbol, df in historical_data.items():
        historical_data[symbol] = strategy.calculate_indicators(df)

    # Determine the common index range
    min_len = min(len(df) for df in historical_data.values())
    warmup = max(
        strategy_params.get("ema_period", DEFAULT_EMA_PERIOD),
        strategy_params.get("sma_period", DEFAULT_SMA_PERIOD),
        strategy_params.get("period", DEFAULT_RSI_PERIOD),
        strategy_params.get("rsi_period", DEFAULT_RSI_PERIOD),
    ) + 5  # Extra padding for indicator warmup

    if min_len <= warmup:
        logger.warning("Not enough data for warmup period")
        return BacktestResult()

    # Walk-forward simulation
    snapshots = []
    total_steps = min_len - warmup

    for i in range(warmup, min_len):
        if progress_callback:
            progress = ((i - warmup) / total_steps) * 100
            progress_callback(progress)

        # Get current prices directly from DF at index i
        current_prices = {}
        for symbol, df in historical_data.items():
            current_prices[symbol] = float(df.iloc[i]["close"])

        # Update portfolio positions
        portfolio.update_positions(current_prices)
        portfolio.check_pending_orders(current_prices)

        # Run strategy
        current_positions = {
            symbol: portfolio.get_position(symbol)
            for symbol in symbols
        }

        # Use optimized signal generation with pre-calculated indicators
        signals = strategy.generate_signals(historical_data, current_positions, index=i)

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
                position = portfolio.get_position(signal.symbol)
                if position:
                    position.stop_loss_price = price * (1 - sl_pct)
                    position.take_profit_price = price * (1 + tp_pct)
                    db.update_position(position)

        # Record snapshot
        total_value = portfolio.get_total_value(current_prices)
        # Use the first symbol's timestamp
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
    result.max_drawdown_pct = _calculate_max_drawdown(snapshots)

    # Store metadata for comparison
    result.strategy_name = strategy_name
    result.strategy_params = dict(strategy_params)
    result.initial_balance = initial_balance
    result.stop_loss_pct = sl_pct
    result.take_profit_pct = tp_pct

    if log_results:
        logger.info(
            f"Backtest complete: {result.total_trades} trades, "
            f"return={result.total_return_pct:.2f}%, "
            f"win_rate={result.win_rate:.1f}%, "
            f"max_drawdown={result.max_drawdown_pct:.2f}%"
        )

    return result


class Backtester:
    """
    Runs a strategy against historical OHLCV data.
    Uses the same Strategy classes and Portfolio logic as live trading.
    """

    def __init__(self, config, exchange):
        self._config = config
        self._exchange = exchange

    def fetch_historical_data(self, symbols: list[str], timeframe: str,
                              days: int) -> dict:
        """Fetch historical data for multiple symbols. Returns {symbol: DataFrame}.

        Public method so sweep callers can fetch once and reuse across runs.
        """
        data = {}
        for symbol in symbols:
            df = self._fetch_historical_data(symbol, timeframe, days)
            if df is not None and len(df) > 0:
                data[symbol] = df
        return data

    def run(self, strategy_name: str, strategy_params: dict,
            symbols: list[str], timeframe: str, days: int = DEFAULT_BACKTEST_DAYS,
            initial_balance: float = DEFAULT_INITIAL_BALANCE,
            stop_loss_pct: float = None,
            take_profit_pct: float = None,
            historical_data: dict = None,
            progress_callback=None,
            log_results=True) -> BacktestResult:
        """Execute a full backtest.

        Args:
            stop_loss_pct: Override config stop-loss (e.g. 0.03 for 3%). None = use config.
            take_profit_pct: Override config take-profit (e.g. 0.06 for 6%). None = use config.
            historical_data: Pre-fetched {symbol: DataFrame}. None = fetch internally.
            progress_callback: Optional callback(pct: float) called during simulation.
            log_results: If False, suppress per-run INFO logs (useful for sweeps).
        """
        if log_results:
            logger.info(
                f"Starting backtest: strategy={strategy_name}, "
                f"symbols={symbols}, timeframe={timeframe}, days={days}"
            )

        # Fetch historical data for all symbols (or use pre-fetched)
        if historical_data is None:
            historical_data = self.fetch_historical_data(symbols, timeframe, days)

        return run_backtest_simulation(
            config=self._config,
            strategy_name=strategy_name,
            strategy_params=strategy_params,
            symbols=symbols,
            timeframe=timeframe,
            days=days,
            initial_balance=initial_balance,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            historical_data=historical_data,
            progress_callback=progress_callback,
            log_results=log_results,
        )

    def _create_strategy(self, name: str, params: dict) -> BaseStrategy:
        return _create_strategy(name, params)

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
        return _calculate_max_drawdown(snapshots)
