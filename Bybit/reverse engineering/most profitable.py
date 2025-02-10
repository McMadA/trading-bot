import ccxt
import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator
import time
from datetime import datetime

# Configuratie
API_KEY = "8JipCzXe9HTR6IRQC8"
API_SECRET = "xaH4j3bL3KPUkUdUjTTWRY6l3lS4XLUQ57oh"
SYMBOL = "ADA/USDT"  # Handelspaar
TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h"]  # Different timeframes for simulation
TRADE_ASSET = "USDT"  # Gebruik de beschikbare USDT voor de order

# Verbind met MEXC
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},  
})

# Functies voor data ophalen en indicatoren

def fetch_data(symbol, timeframe, limit=500, retries=3, delay=5):
    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not candles:
                print(f"Geen gegevens ontvangen van de API voor {timeframe}.")
                return None
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            print(f"Fout bij ophalen van data voor {timeframe}: {e}")
            time.sleep(delay)
    return None

def calculate_sma(data, period=20):
    sma = SMAIndicator(data["close"], window=period)
    data["sma"] = sma.sma_indicator()
    return data

def calculate_ema(data, period=10):
    ema = EMAIndicator(data["close"], window=period)
    data["ema"] = ema.ema_indicator()
    return data

def check_crossovers(data):
    """ Geeft een signaal wanneer EMA de SMA kruist. """
    data["ema_boven_sma"] = (data["ema"] > data["sma"]).astype(bool)  # Zorg dat het een boolean is
    data["bullish_cross"] = (data["ema_boven_sma"] & (~data["ema_boven_sma"].shift(1).astype(bool).fillna(False))).astype(bool)
    data["bearish_cross"] = (~data["ema_boven_sma"] & (data["ema_boven_sma"].shift(1).astype(bool).fillna(False))).astype(bool)
    return data

def simulate_trading(data, start_usdt=100, start_ada=100):
    """ Simuleert trading en houdt saldo's bij. """
    usdt_balance = start_usdt
    ada_balance = start_ada

    usdt_balances = []
    ada_balances = []

    for index, row in data.iterrows():
        close_price = row["close"]

        if row["bullish_cross"]:
            if usdt_balance >= 100:
                ada_bought = 100 / close_price
                ada_balance += ada_bought
                usdt_balance -= 100

        if row["bearish_cross"]:
            if ada_balance * close_price >= 100:
                ada_sold = 100 / close_price
                ada_balance -= ada_sold
                usdt_balance += 100

        usdt_balances.append(usdt_balance)
        ada_balances.append(ada_balance)

    data["usdt_balance"] = usdt_balances
    data["ada_balance"] = ada_balances
    return data

def run_simulations(data, ema_periods=range(5, 50), sma_periods=range(5, 50), timeframes=["5m", "15m", "30m", "1h", "4h"]):
    """Run simulations with different EMA, SMA periods and timeframes and show the most profitable result."""
    best_profit = -float('inf')
    best_combination = None
    best_timeframe = None

    for timeframe in timeframes:
        print(f"Running simulations for {timeframe}...")
        for ema_period in ema_periods:
            for sma_period in sma_periods:
                # Fetch data for the current timeframe
                data = fetch_data(SYMBOL, timeframe)

                if data is None:
                    print(f"Skipping {timeframe} due to missing data.")
                    continue

                # Calculate the EMA and SMA indicators with the chosen periods
                data = calculate_ema(data, period=ema_period)
                data = calculate_sma(data, period=sma_period)
                data = check_crossovers(data)
                
                # Simulate trading for this combination
                data_with_balances = simulate_trading(data, start_usdt=100, start_ada=100)

                # Calculate the final balance (USDT + ADA value at last close price)
                final_usdt_balance = data_with_balances["usdt_balance"].iloc[-1]
                final_ada_balance = data_with_balances["ada_balance"].iloc[-1]
                final_balance = final_usdt_balance + final_ada_balance * data_with_balances["close"].iloc[-1]

                # Calculate profit
                profit = final_balance - 100  # Starting with 100 USDT
                print(f"EMA{ema_period} + SMA{sma_period} -> Profit: ${profit:.2f}")

                # Check for the most profitable combination
                if profit > best_profit:
                    best_profit = profit
                    best_combination = (ema_period, sma_period)
                    best_timeframe = timeframe

    return best_combination, best_profit, best_timeframe

# Simulatie van trading
def main():
    # Run simulations with different combinations of EMA, SMA periods and timeframes
    best_combination, best_profit, best_timeframe = run_simulations(data=None)

    print(f"\nMost profitable combination: EMA{best_combination[0]} + SMA{best_combination[1]} at {best_timeframe}")
    print(f"Best profit: ${best_profit:.2f}")

if __name__ == "__main__":
    main()
