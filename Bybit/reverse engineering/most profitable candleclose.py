import ccxt
import pandas as pd
from ta.trend import SMAIndicator
import time
from datetime import datetime

# Configuratie
API_KEY = "8JipCzXe9HTR6IRQC8"
API_SECRET = "xaH4j3bL3KPUkUdUjTTWRY6l3lS4XLUQ57oh"
SYMBOL = "ADA/USDT"  # Handelspaar
TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h"]  # Different timeframes for simulation
STANDARD_CANDLES = 1000  # Number of candles for 4h timeframe (standard)

# Verbind met MEXC
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},
})

# Define the duration of each timeframe in hours
timeframe_durations = {
    "5m": 5 / 60,
    "15m": 15 / 60,
    "30m": 30 / 60,
    "1h": 1,
    "4h": 4
}

# Functies voor data ophalen en indicatoren
def fetch_data(symbol, timeframe, limit=5000, retries=3, delay=5):
    candles_needed = STANDARD_CANDLES * (timeframe_durations["4h"] / timeframe_durations[timeframe])
    candles_needed = int(candles_needed)  # Ensure we get an integer number of candles

    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=candles_needed)
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

def check_crossovers(data):
    """ Geeft een signaal wanneer candle close de sma kruist. """
    data["close_boven_sma"] = (data["close"] > data["sma"]).astype(bool)  # Zorg dat het een boolean is
    data["bullish_cross"] = (data["close_boven_sma"] & (~data["close_boven_sma"].shift(1).astype(bool).fillna(False))).astype(bool)
    data["bearish_cross"] = (~data["close_boven_sma"] & (data["close_boven_sma"].shift(1).astype(bool).fillna(False))).astype(bool)
    return data

def simulate_trading(data, start_usdt=100, start_ada=100):
    """ Simuleert trading en houdt saldo's bij. """
    usdt_balance = start_usdt
    ada_balance = start_ada

    usdt_balances = []
    ada_balances = []

    initial_usdt_value = start_usdt + (start_ada * data["close"].iloc[0])

    for index, row in data.iterrows():
        close_price = row["close"]
        timestamp = row["timestamp"]

        if row["bullish_cross"]:
            # Buy ADA based on available USDT balance
            if usdt_balance > 0:
                ada_bought = usdt_balance / close_price  # Buy with all available USDT
                ada_balance += ada_bought
                usdt_balance = 0  # After buying, all USDT is spent
                print(f"{timestamp}: Koop ADA voor {close_price} USDT -- Saldo ADA: {ada_balance:.2f}, Saldo USDT: {usdt_balance:.2f}")

        if row["bearish_cross"]:
            # Sell ADA based on available ADA balance
            if ada_balance > 0:
                usdt_received = ada_balance * close_price  # Sell all available ADA
                usdt_balance += usdt_received
                ada_balance = 0  # After selling, all ADA is sold
                print(f"{timestamp}: Verkoop ADA voor {close_price} USDT -- Saldo USDT: {usdt_balance:.2f}, saldo ADA: {ada_balance:.2f}")

        usdt_balances.append(usdt_balance)
        ada_balances.append(ada_balance)

    data["usdt_balance"] = usdt_balances
    data["ada_balance"] = ada_balances

    final_usdt_balance = usdt_balance + (ada_balance * data["close"].iloc[-1])
    percentage_profit = ((final_usdt_balance - initial_usdt_value) / initial_usdt_value) * 100
    print(f"Percentage winst: {percentage_profit:.2f}%")
    print(f"Saldo USDT: {usdt_balance:.2f}, Saldo ADA: {ada_balance:.2f}")

    return data, percentage_profit

def run_simulations(data, sma_periods=range(19, 20), timeframes=["5m", "15m", "30m", "1h", "4h"]):
    """Run simulations with different SMA periods and timeframes and show the most profitable result."""
    best_profit = -float('inf')
    best_sma = None
    best_timeframe = None
    best_percentage_profit = None

    for timeframe in timeframes:
        print(f"Running simulations for {timeframe}...")

        # Fetch data for the current timeframe
        data = fetch_data(SYMBOL, timeframe)
        if data is None:
            print(f"Skipping {timeframe} due to missing data.")
            continue

        for sma_period in sma_periods:
            print(f"Running simulations for SMA{sma_period}...")
            # Calculate the SMA with the chosen period
            data_copy = data.copy()
            data_copy = calculate_sma(data_copy, period=sma_period)
            
            # Check for crossovers after calculating the SMA
            data_copy = check_crossovers(data_copy)
            
            # Simulate trading for this combination
            data_with_balances, percentage_profit = simulate_trading(data_copy, start_usdt=100, start_ada=100)

            # Check for the most profitable combination
            if percentage_profit > best_profit:
                best_profit = percentage_profit
                best_sma = sma_period
                best_timeframe = timeframe
                best_percentage_profit = percentage_profit

    return best_sma, best_percentage_profit, best_timeframe

# Simulatie van trading
def main():
    # Run simulations with different combinations of SMA periods and timeframes
    best_sma, best_profit, best_timeframe = run_simulations(data=None)

    print(f"\nMost profitable combination: SMA{best_sma} at {best_timeframe}")
    print(f"Best profit: {best_profit:.2f}%")




if __name__ == "__main__":
    main()
