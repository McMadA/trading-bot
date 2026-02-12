# Paper Trading System

Automated cryptocurrency paper trading system with real-time market data, configurable strategies, and a web dashboard.

## Features

- **Paper trading** with simulated orders using real market data from Binance (no API keys required)
- **Three trading strategies**: EMA/SMA Crossover, RSI, and Combined (EMA/SMA + RSI confirmation)
- **Risk management**: Configurable position sizing, stop-loss, take-profit
- **Web dashboard**: Real-time portfolio tracking, candlestick charts, trade history, strategy controls
- **Backtesting**: Test strategies against historical data from the dashboard
- **SQLite persistence**: All trades, positions, and portfolio history stored in database

## Quick Start

### 1. Install dependencies

```bash
cd paper-trading
pip install -r requirements.txt
```

### 2. Configure (optional)

Edit `config.yaml` to adjust:
- Trading pairs (default: BTC/USDT, ETH/USDT, SOL/USDT)
- Strategy and parameters
- Risk management settings
- Initial balance (default: $10,000 USDT)

### 3. Run

```bash
python main.py
```

Open the dashboard at **http://localhost:5000**

## Configuration

All settings are in `config.yaml`:

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| `trading.pairs` | list | BTC/USDT, ETH/USDT, SOL/USDT | Trading pairs to monitor |
| `trading.default_timeframe` | string | 15m | Candle timeframe |
| `trading.initial_balance` | float | 10000.0 | Starting USDT balance |
| `trading.fee_rate` | float | 0.001 | Simulated trading fee (0.1%) |
| `strategy.active` | string | ema_sma_crossover | Active strategy |
| `risk_management.max_position_pct` | float | 0.25 | Max 25% of portfolio per position |
| `risk_management.stop_loss_pct` | float | 0.03 | 3% stop-loss |
| `risk_management.take_profit_pct` | float | 0.06 | 6% take-profit |
| `risk_management.max_open_positions` | int | 4 | Max concurrent positions |
| `scheduler.interval_seconds` | int | 60 | Engine tick interval |
| `dashboard.port` | int | 5000 | Dashboard port |

## Strategies

### EMA/SMA Crossover (`ema_sma_crossover`)
- **BUY** when EMA crosses above SMA on completed candles
- **SELL** when EMA crosses below SMA
- Parameters: `ema_period` (default: 10), `sma_period` (default: 20)

### RSI (`rsi`)
- **BUY** when RSI crosses up through the oversold level
- **SELL** when RSI crosses down through the overbought level
- Parameters: `period` (default: 14), `overbought` (default: 70), `oversold` (default: 30)

### Combined (`combined`)
- EMA/SMA crossover confirmed by RSI filter
- **BUY** requires crossover AND RSI not overbought
- **SELL** requires crossover AND RSI not oversold

Strategies can be switched at runtime from the dashboard without restarting.

## Dashboard

The web dashboard at `http://localhost:5000` displays:
- Portfolio value and P&L
- Live price ticker for all monitored pairs
- Candlestick charts with indicator overlays
- Active positions with entry price, current price, and unrealized P&L
- Trade history with per-trade P&L
- Equity curve tracking portfolio value over time
- Performance metrics (win rate, average P&L, best/worst trade)
- Strategy controls to switch strategies and adjust parameters
- System logs

### Backtesting

Visit `http://localhost:5000/backtest` to run backtests against historical data. Configure strategy, parameters, symbols, timeframe, and lookback period.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio` | Portfolio summary |
| GET | `/api/positions` | Open positions |
| GET | `/api/orders` | Recent orders |
| GET | `/api/trades` | Completed trades |
| GET | `/api/prices` | Current prices |
| GET | `/api/chart/<symbol>` | OHLCV + indicator data |
| GET | `/api/performance` | Performance metrics + equity curve |
| GET | `/api/logs` | System logs |
| GET | `/api/strategy` | Current strategy info |
| POST | `/api/strategy` | Change strategy |
| GET | `/api/engine/status` | Engine status |
| POST | `/api/backtest` | Run backtest |

## Project Structure

```
paper-trading/
├── main.py                     # Entry point
├── config.yaml                 # Configuration
├── requirements.txt            # Dependencies
├── src/
│   ├── utils/
│   │   ├── config.py           # YAML config loader
│   │   └── logger.py           # Logging with dashboard handler
│   ├── data/
│   │   ├── models.py           # Domain models (Order, Position, etc.)
│   │   └── database.py         # SQLite operations
│   ├── trading/
│   │   ├── engine.py           # Trading engine (data fetch, strategy dispatch)
│   │   ├── portfolio.py        # Virtual exchange / portfolio manager
│   │   ├── strategy.py         # Strategy implementations
│   │   └── backtester.py       # Historical backtesting
│   └── dashboard/
│       ├── app.py              # Flask app factory
│       ├── routes.py           # API + page routes
│       ├── templates/          # HTML templates
│       └── static/             # CSS + JavaScript
```
