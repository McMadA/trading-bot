import ccxt
import pandas as pd
from ta.trend import SMAIndicator
import time
from datetime import datetime

# Configuratie
API_KEY = ""
API_SECRET = ""
SYMBOL = "ADA/USDT"
TIMEFRAME = "5m"
TRADE_ASSET = "USDT"

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},
})

def wait_until_next_candle(interval_minutes=5):
    now = datetime.now()
    seconds_to_next_candle = (
        interval_minutes * 60 - (now.minute % interval_minutes) * 60 - now.second
    )
    time.sleep(seconds_to_next_candle)

def get_available_balance(asset):
    try:
        balance = exchange.fetch_balance({'type': 'spot'})
        return balance['free'].get(asset, 0)
    except Exception:
        return None

def fetch_data(symbol, timeframe, limit=49, retries=3, delay=5):
    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if candles:
                df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                return df
        except Exception:
            time.sleep(delay)
    return None

def calculate_sma(data, period=20):
    sma = SMAIndicator(data["close"], window=period)
    data["sma20"] = sma.sma_indicator()
    return data

def place_order(side, symbol, amount):
    try:
        order = exchange.create_market_order(symbol, side, amount)
        return order
    except Exception:
        return None

def main():
    while True:
        wait_until_next_candle()
        data = fetch_data(SYMBOL, TIMEFRAME)
        if data is None:
            continue
        data = calculate_sma(data)
        
        last_candle = data.iloc[-1]
        previous_candle = data.iloc[-2]

        if previous_candle["close"] < previous_candle["sma20"] and last_candle["close"] > last_candle["sma20"]:
            available_balance = get_available_balance(TRADE_ASSET)
            if available_balance > 2:
                amount_to_buy = available_balance / last_candle["close"]
                place_order("buy", SYMBOL, amount_to_buy)

        elif previous_candle["close"] > previous_candle["sma20"] and last_candle["close"] < last_candle["sma20"]:
            available_balance = get_available_balance("ADA")
            if available_balance > 0:
                place_order("sell", SYMBOL, available_balance)

if __name__ == "__main__":
    main()
