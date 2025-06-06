import time
import hashlib
import hmac
import requests

# Vul je API-sleutels in
api_key = 'YOUR_API_KEY'
api_secret = 'YOUR_API_SECRET'

# Blofin API Basis URL
base_url = 'https://api.blofin.com'

# Voorbeeld van een future order
symbol = 'BTCUSDT'     # Het handelspaar, bijvoorbeeld BTC/USDT
side = 'buy'           # 'buy' voor een long positie, 'sell' voor short
price = 30000          # De prijs waarop je de order wilt plaatsen
quantity = 0.01        # Hoeveelheid contracten
leverage = 10          # Hefboomfactor

# Functie voor het genereren van de handtekening
def generate_signature(api_key, api_secret, params):
    # Params moeten worden gesorteerd op sleutel en dan samengevoegd
    params_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    payload = f"{api_key}{params_string}{api_secret}"
    
    # Genereer de HMAC handtekening
    signature = hmac.new(api_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
    
    return signature

# Functie om een future order te plaatsen
def place_future_order(symbol, side, price, quantity, leverage):
    # De parameters voor de order
    params = {
        'symbol': symbol,
        'side': side,  # 'buy' of 'sell'
        'price': price,
        'quantity': quantity,
        'leverage': leverage,
        'timestamp': str(int(time.time() * 1000)),  # Tijdstempel in milliseconden
    }

    # Genereer de handtekening
    signature = generate_signature(api_key, api_secret, params)

    # Voeg de handtekening toe aan de parameters
    params['signature'] = signature

    # Stel de headers in voor de API-aanroep
    headers = {
        'API-KEY': api_key,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # API-aanroep voor het plaatsen van de future order
    response = requests.post(f"{base_url}/api/v1/order", data=params, headers=headers)

    # Return de response van de API
    return response.json()



# Plaats de future order
order_response = place_future_order(symbol, side, price, quantity, leverage)

# Print de response van de API
print(order_response)



# import requests
# import pandas as pd
# from datetime import datetime, timedelta
# import time
# import threading
# from flask import Flask, render_template

# # Configuratie
# API_KEY = "YOUR_BLOFIN_API_KEY"
# API_SECRET = "YOUR_BLOFIN_API_SECRET"
# SYMBOL = "ADA-USDT"  # Pas aan naar jouw gewenste handelspaar
# TIMEFRAME = "30m"  # Tijdframe van candles
# BASE_URL = "https://api.blofin.com"  # Blofin API Base URL

# # Logberichten voor de Flask-interface
# log_messages = []

# def add_log(message):
#     """Voeg een logbericht toe aan de lijst en druk af."""
#     timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     log_message = f"{timestamp} - {message}"
#     log_messages.append(log_message)
#     print(log_message)

# # Flask-webserver
# app = Flask(__name__)

# @app.route("/")
# def home():
#     """Render de logs in de index.html file."""
#     logs_html = " \n ".join(log_messages[-100:])  # Combineer de laatste 100 logs
#     return render_template("index.html", logs=logs_html)

# def get_headers():
#     """Genereer headers met API-key en signature."""
#     return {
#         "Content-Type": "application/json",
#         "X-API-KEY": API_KEY,
#     }

# def fetch_market_data(symbol, timeframe):
#     """Haalt marktdata op van Blofin."""
#     endpoint = f"{BASE_URL}/market/ohlcv"
#     params = {"symbol": symbol, "interval": timeframe, "limit": 49}

#     try:
#         response = requests.get(endpoint, headers=get_headers(), params=params)
#         response.raise_for_status()
#         data = response.json()

#         if data.get("code") != 200:
#             add_log(f"Fout bij ophalen van marktdata: {data}")
#             return None

#         candles = data["data"]
#         df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
#         df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
#         df["close"] = df["close"].astype(float)
#         return df
#     except Exception as e:
#         add_log(f"Fout bij ophalen van marktdata: {e}")
#         return None

# def fetch_balance(asset):
#     """Haal de balans op van een specifiek asset."""
#     endpoint = f"{BASE_URL}/account/balance"
#     try:
#         response = requests.get(endpoint, headers=get_headers())
#         response.raise_for_status()
#         data = response.json()

#         if data.get("code") != 200:
#             add_log(f"Fout bij ophalen van balans: {data}")
#             return 0

#         for item in data["data"]:
#             if item["asset"] == asset:
#                 return float(item["available"])
#         return 0
#     except Exception as e:
#         add_log(f"Fout bij ophalen van balans: {e}")
#         return 0

# def place_order(side, symbol, amount):
#     """Plaats een marktorder op Blofin."""
#     endpoint = f"{BASE_URL}/order/place"
#     payload = {
#         "symbol": symbol,
#         "side": side,
#         "type": "market",
#         "quantity": amount
#     }

#     try:
#         response = requests.post(endpoint, headers=get_headers(), json=payload)
#         response.raise_for_status()
#         data = response.json()

#         if data.get("code") != 200:
#             add_log(f"Fout bij plaatsen van order: {data}")
#             return None

#         add_log(f"Order geplaatst: {side} {amount} {symbol}")
#         return data["data"]
#     except Exception as e:
#         add_log(f"Fout bij plaatsen van order: {e}")
#         return None

# def calculate_sma(data, period=20):
#     """Bereken de SMA op basis van sluitprijzen."""
#     data[f"sma{period}"] = data["close"].rolling(window=period).mean()
#     return data

# def wait_until_next_candle(interval_minutes=30):
#     """Wacht tot het begin van de volgende candle op een specifiek interval."""
#     now = datetime.now()
#     seconds_to_next_candle = (
#         interval_minutes * 60 - (now.minute % interval_minutes) * 60 - now.second
#     )
#     add_log(f"Wachten tot de volgende candle: {seconds_to_next_candle} seconden...")
#     time.sleep(seconds_to_next_candle)

# def main():
#     while True:
#         try:
#             wait_until_next_candle(interval_minutes=30)
#             data = fetch_market_data(SYMBOL, TIMEFRAME)

#             if data is None or data.empty:
#                 continue

#             data = calculate_sma(data)
#             last_candle = data.iloc[-2]
#             previous_candle = data.iloc[-3]

#             if previous_candle["close"] < previous_candle["sma20"] and last_candle["close"] > last_candle["sma20"]:
#                 balance = fetch_balance("USDT")
#                 if balance > 2:
#                     amount = balance / last_candle["close"]
#                     place_order("buy", SYMBOL, amount)

#             elif previous_candle["close"] > previous_candle["sma20"] and last_candle["close"] < last_candle["sma20"]:
#                 balance = fetch_balance("ADA")
#                 if balance > 0:
#                     place_order("sell", SYMBOL, balance)

#         except Exception as e:
#             add_log(f"Fout in de hoofdloop: {e}")
#             time.sleep(60)

# if __name__ == "__main__":
#     bot_thread = threading.Thread(target=main, daemon=True)
#     bot_thread.start()
#     app.run(host="0.0.0.0", port=5000)

