import sys
from unittest.mock import MagicMock, patch

# Mock dependencies
mock_pd = MagicMock()
# Mock isna to behave reasonably
def mock_isna(obj):
    if obj is None: return True
    try:
        import numpy as np
        if isinstance(obj, float) and np.isnan(obj): return True
    except:
        pass
    return False
mock_pd.isna = mock_isna
sys.modules["pandas"] = mock_pd

sys.modules["ccxt"] = MagicMock()
sys.modules["ta"] = MagicMock()
sys.modules["ta.trend"] = MagicMock()
sys.modules["ta.momentum"] = MagicMock()
sys.modules["apscheduler"] = MagicMock()
sys.modules["apscheduler.schedulers.background"] = MagicMock()

import pytest
from src.trading.backtester import run_backtest_simulation, BacktestResult
from src.trading.strategy import BaseStrategy

def test_optimized_backtest_calls():
    # Setup mocks
    mock_df = MagicMock()
    mock_df.__len__.return_value = 100 # 100 candles

    # Mock iloc to return a MagicMock that returns a float for "close"
    # and a string for "timestamp"
    def mock_getitem(key):
        if key == "close": return 100.0
        if key == "timestamp":
            ts = MagicMock()
            ts.isoformat.return_value = "2023-01-01T00:00:00"
            return ts
        return 0.0

    mock_row = MagicMock()
    mock_row.__getitem__.side_effect = mock_getitem

    # Allow df.iloc[i] to return mock_row
    mock_df.iloc.__getitem__.return_value = mock_row

    historical_data = {"BTC/USDT": mock_df}

    config = {
        "trading.fee_rate": 0.001,
        "risk_management.stop_loss_pct": 0.03,
        "risk_management.take_profit_pct": 0.06
    }

    # Mock strategy
    with patch("src.trading.backtester._create_strategy") as mock_create_strategy:
        mock_strategy = MagicMock()
        mock_strategy.calculate_indicators.return_value = mock_df # Return same mock df
        mock_strategy.generate_signals.return_value = [] # No signals for now
        mock_strategy.name = "mock_strategy"

        mock_create_strategy.return_value = mock_strategy

        # Run backtest
        result = run_backtest_simulation(
            config=config,
            strategy_name="ema_sma_crossover",
            strategy_params={"ema_period": 10, "sma_period": 20},
            symbols=["BTC/USDT"],
            timeframe="1h",
            days=30,
            initial_balance=10000.0,
            stop_loss_pct=None,
            take_profit_pct=None,
            historical_data=historical_data
        )

        # Verify calculate_indicators called once (per symbol)
        mock_strategy.calculate_indicators.assert_called()
        assert mock_strategy.calculate_indicators.call_count == 1

        # Verify generate_signals called with index
        # Warmup is max(periods) + 5 = 20 + 5 = 25
        # Loop runs from 25 to 100
        expected_calls = 100 - 25
        assert mock_strategy.generate_signals.call_count == expected_calls

        # Check arguments of the last call
        args, kwargs = mock_strategy.generate_signals.call_args
        assert kwargs["index"] == 99
        # args[0] should be the historical_data dict (which contains mock_df)
        assert args[0]["BTC/USDT"] == mock_df

def test_progress_callback():
    # Setup mocks
    mock_df = MagicMock()
    mock_df.__len__.return_value = 50

    def mock_getitem(key):
        if key == "close": return 100.0
        if key == "timestamp":
            ts = MagicMock()
            ts.isoformat.return_value = "2023-01-01T00:00:00"
            return ts
        return 0.0

    mock_row = MagicMock()
    mock_row.__getitem__.side_effect = mock_getitem
    mock_df.iloc.__getitem__.return_value = mock_row

    historical_data = {"BTC/USDT": mock_df}

    config = {}

    progress_callback = MagicMock()

    with patch("src.trading.backtester._create_strategy") as mock_create_strategy:
        mock_strategy = MagicMock()
        mock_strategy.calculate_indicators.return_value = mock_df
        mock_strategy.generate_signals.return_value = []
        mock_create_strategy.return_value = mock_strategy

        run_backtest_simulation(
            config=config,
            strategy_name="test",
            strategy_params={"period": 10},
            symbols=["BTC/USDT"],
            timeframe="1h",
            days=1,
            initial_balance=10000,
            stop_loss_pct=0.01,
            take_profit_pct=0.02,
            historical_data=historical_data,
            progress_callback=progress_callback
        )

        assert progress_callback.called
