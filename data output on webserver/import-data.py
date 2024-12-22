import ccxt
import pandas as pd
from ta.trend import SMAIndicator
import time
from datetime import datetime
from flask import Flask, render_template, jsonify
import threading

# Configuratie
API_KEY = ""
API_SECRET = ""
SYMBOL = "ADA/USDT"  # Pas aan naar jouw gewenste handelspaar
TIMEFRAME = "15m"  # Tijdframe van candles
LOT_SIZE = 5  # Hoeveelheid crypto om te handelen

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "future"},  # Activeer futures trading
})

# Flask setup
app = Flask(__name__)

# Global variables to track data and positions
counter = 0
last_data = None
current_position = None

# Function to fetch market data
def fetch_data(symbol, timeframe, limit=50):
    """Haalt markthistorie op"""
    candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# Function to calculate the SMA
def calculate_sma(data, period=20):
    """Bereken SMA op sluitprijzen"""
    sma = SMAIndicator(data["close"], window=period)
    data["sma20"] = sma.sma_indicator()
    return data
    
@app.route('/')
def index():
    # Fetch data, calculate SMA and show
    df = fetch_data(SYMBOL, TIMEFRAME)
    df = calculate_sma(df)
    
    # Convert the DataFrame to a list of dictionaries (flattened)
    df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')  # Convert datetime to string
    result = df.tail(5).to_dict(orient='records')  # Get the last 5 rows
    
    # Return the data as JSON
    return render_template('index.html', data=result, symbol=SYMBOL)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)