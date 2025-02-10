import ccxt
import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator
import time
from datetime import datetime

# Configuratie
API_KEY = "8JipCzXe9HTR6IRQC8"
API_SECRET = "xaH4j3bL3KPUkUdUjTTWRY6l3lS4XLUQ57oh"
SYMBOL = "ADA/USDT"  # Handelspaar
TIMEFRAME = "1h"  # Tijdframe van candles
TRADE_ASSET = "USDT"  # Gebruik de beschikbare USDT voor de order

# Verbind met MEXC
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},  
})

# Functies voor data ophalen en indicatoren

def fetch_data(symbol, timeframe, limit=200, retries=3, delay=5):
    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not candles:
                print("Geen gegevens ontvangen van de API.")
                return None
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except Exception as e:
            print(f"Fout bij ophalen van data: {e}")
            time.sleep(delay)
    return None

def calculate_sma(data, period=8):
    sma = SMAIndicator(data["close"], window=period)
    data["sma"] = sma.sma_indicator()
    return data

def calculate_ema(data, period=19):
    ema = EMAIndicator(data["close"], window=period)
    data["ema"] = ema.ema_indicator()
    return data

def check_crossovers(data):
    """ Geeft een signaal wanneer EMA de SMA kruist. """
    data["ema_boven_sma"] = (data["ema"] > data["sma"]).astype(bool)  # Zorg dat het een boolean is
    data["bullish_cross"] = data["ema_boven_sma"] & ~data["ema_boven_sma"].shift(1).fillna(False)
    data["bearish_cross"] = ~data["ema_boven_sma"] & data["ema_boven_sma"].shift(1).fillna(False)
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
                print(f"{row['timestamp']} - KOOP: ${100} aan ADA tegen ${close_price} per ADA")

        if row["bearish_cross"]:
            if ada_balance * close_price >= 100:
                ada_sold = 100 / close_price
                ada_balance -= ada_sold
                usdt_balance += 100
                print(f"{row['timestamp']} - VERKOOP: ${100} aan ADA tegen ${close_price} per ADA")

        usdt_balances.append(usdt_balance)
        ada_balances.append(ada_balance)

    data["usdt_balance"] = usdt_balances
    data["ada_balance"] = ada_balances
    return data

def main():
    data = fetch_data(SYMBOL, TIMEFRAME)
    if data is None:
        print("Geen gegevens ontvangen, opnieuw proberen.")
        return
    data = calculate_ema(data)
    data = calculate_sma(data)
    data = check_crossovers(data)
    data = simulate_trading(data)

    data.to_csv("trading_results2.csv", index=False)
    print("Results saved to trading_results.csv")


    print(data[["timestamp", "close", "ema", "sma", "bullish_cross", "bearish_cross", "usdt_balance", "ada_balance"]])
if __name__ == "__main__":
    main()
