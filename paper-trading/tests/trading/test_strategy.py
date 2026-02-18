import sys
from unittest.mock import MagicMock

# Mock external dependencies before they are imported by the strategy
mock_pd = MagicMock()
# We need pd.isna to work at least for simple cases
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

mock_ta = MagicMock()
sys.modules["ta"] = mock_ta
sys.modules["ta.trend"] = MagicMock()
sys.modules["ta.momentum"] = MagicMock()
# Mock ccxt too if needed elsewhere, although strategy.py doesn't seem to import it directly
sys.modules["ccxt"] = MagicMock()

import pytest
from datetime import datetime

# Now import the components to test
# Since we mocked pandas, we might need to mock how DataFrame works if the strategy uses it
# but CombinedStrategy.generate_signals uses df.iloc and df.items which we can mock.

from src.trading.strategy import CombinedStrategy, Signal
from src.data.models import OrderSide, Position, PositionStatus

@pytest.fixture
def strategy_config():
    return {
        "ema_period": 10,
        "sma_period": 20,
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30
    }

@pytest.fixture
def strategy(strategy_config):
    return CombinedStrategy(strategy_config)

def create_mock_df_row(ema, sma, rsi):
    row = MagicMock()
    row.__getitem__.side_effect = lambda key: {"ema": ema, "sma": sma, "rsi": rsi}[key]
    return row

def test_combined_strategy_buy_signal(strategy):
    # EMA crosses above SMA and RSI is not overbought (< 70)

    # Mock df
    mock_df = MagicMock()
    mock_df.__len__.return_value = 10

    prev_row = create_mock_df_row(90.0, 100.0, 50.0)
    last_row = create_mock_df_row(110.0, 100.0, 50.0)

    def mock_iloc_getitem(idx):
        if idx == -3: return prev_row
        if idx == -2: return last_row
        return MagicMock()

    mock_df.iloc.__getitem__.side_effect = mock_iloc_getitem

    strategy.calculate_indicators = MagicMock(return_value=mock_df)

    data = {"BTC/USDT": mock_df}
    current_positions = {"BTC/USDT": None}

    signals = strategy.generate_signals(data, current_positions)

    assert len(signals) == 1
    assert signals[0].side == OrderSide.BUY
    assert signals[0].symbol == "BTC/USDT"
    assert "EMA/SMA crossover" in signals[0].reason

def test_combined_strategy_no_buy_if_overbought(strategy):
    # EMA crosses above SMA but RSI is overbought (>= 70)
    mock_df = MagicMock()
    mock_df.__len__.return_value = 10

    prev_row = create_mock_df_row(90.0, 100.0, 75.0)
    last_row = create_mock_df_row(110.0, 100.0, 75.0)

    mock_df.iloc.__getitem__.side_effect = lambda idx: prev_row if idx == -3 else last_row

    strategy.calculate_indicators = MagicMock(return_value=mock_df)

    data = {"BTC/USDT": mock_df}
    current_positions = {"BTC/USDT": None}

    signals = strategy.generate_signals(data, current_positions)

    assert len(signals) == 0

def test_combined_strategy_sell_signal(strategy):
    # EMA crosses below SMA and RSI is not oversold (> 30)
    mock_df = MagicMock()
    mock_df.__len__.return_value = 10

    prev_row = create_mock_df_row(110.0, 100.0, 50.0)
    last_row = create_mock_df_row(90.0, 100.0, 50.0)

    mock_df.iloc.__getitem__.side_effect = lambda idx: prev_row if idx == -3 else last_row

    strategy.calculate_indicators = MagicMock(return_value=mock_df)

    data = {"BTC/USDT": mock_df}
    mock_position = Position(
        id=1, symbol="BTC/USDT", side=OrderSide.BUY, quantity=1.0,
        entry_price=10.0, current_price=10.0, stop_loss_price=None,
        take_profit_price=None, unrealized_pnl=0.0, realized_pnl=0.0,
        status=PositionStatus.OPEN, opened_at=datetime.now(),
        closed_at=None, entry_order_id=1, exit_order_id=None
    )
    current_positions = {"BTC/USDT": mock_position}

    signals = strategy.generate_signals(data, current_positions)

    assert len(signals) == 1
    assert signals[0].side == OrderSide.SELL
    assert signals[0].symbol == "BTC/USDT"
    assert "EMA/SMA bearish crossover" in signals[0].reason

def test_combined_strategy_no_sell_if_oversold(strategy):
    # EMA crosses below SMA but RSI is oversold (<= 30)
    mock_df = MagicMock()
    mock_df.__len__.return_value = 10

    prev_row = create_mock_df_row(110.0, 100.0, 25.0)
    last_row = create_mock_df_row(90.0, 100.0, 25.0)

    mock_df.iloc.__getitem__.side_effect = lambda idx: prev_row if idx == -3 else last_row

    strategy.calculate_indicators = MagicMock(return_value=mock_df)

    data = {"BTC/USDT": mock_df}
    mock_position = Position(
        id=1, symbol="BTC/USDT", side=OrderSide.BUY, quantity=1.0,
        entry_price=10.0, current_price=10.0, stop_loss_price=None,
        take_profit_price=None, unrealized_pnl=0.0, realized_pnl=0.0,
        status=PositionStatus.OPEN, opened_at=datetime.now(),
        closed_at=None, entry_order_id=1, exit_order_id=None
    )
    current_positions = {"BTC/USDT": mock_position}

    signals = strategy.generate_signals(data, current_positions)

    assert len(signals) == 0

def test_combined_strategy_insufficient_data(strategy):
    # Less than 3 candles
    mock_df = MagicMock()
    mock_df.__len__.return_value = 2
    data = {"BTC/USDT": mock_df}
    current_positions = {"BTC/USDT": None}

    signals = strategy.generate_signals(data, current_positions)
    assert len(signals) == 0

def test_combined_strategy_nan_values(strategy):
    mock_df = MagicMock()
    mock_df.__len__.return_value = 10

    # Simulate pd.isna returning True for ema
    prev_row = create_mock_df_row(90.0, 100.0, 50.0)
    last_row = MagicMock()
    last_row.__getitem__.side_effect = lambda key: None if key == "ema" else 100.0

    mock_df.iloc.__getitem__.side_effect = lambda idx: prev_row if idx == -3 else last_row

    strategy.calculate_indicators = MagicMock(return_value=mock_df)

    data = {"BTC/USDT": mock_df}
    current_positions = {"BTC/USDT": None}

    signals = strategy.generate_signals(data, current_positions)
    assert len(signals) == 0
