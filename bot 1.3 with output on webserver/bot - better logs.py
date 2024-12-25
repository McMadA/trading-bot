import ccxt
import pandas as pd
from ta.trend import EMAIndicator
import time
from datetime import datetime, timedelta
import threading

#v1.1
# Configuratie
API_KEY = ""
API_SECRET = ""
SYMBOL = "ADA/USDT"  # Pas aan naar jouw gewenste handelspaar
TIMEFRAME = "15m"  # Tijdframe van candles
TRADE_ASSET = "USDT"  # Gebruik de beschikbare USDT voor de order

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},  
})

def add_log(message):
    """Voeg een logbericht toe aan de lijst en druk af."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"{timestamp} - {message}"
    log_messages.append(log_message)
    print(log_message)

from flask import Flask, render_template

app = Flask(__name__)
log_messages = []  # Storage for log messages

@app.route("/")
def home():
    """Render the logs in the index.html file."""
    logs_html = " \n ".join(log_messages[-100:])  # Combine the last 100 logs
    return render_template("index.html", logs=logs_html)



def wait_until_next_candle(interval_minutes=15):
    """Wacht tot het begin van de volgende candle op een specifiek interval."""
    now = datetime.now()
    # Bereken het aantal seconden tot het volgende interval
    seconds_to_next_candle = (
        interval_minutes * 60 - (now.minute % interval_minutes) * 60 - now.second
    )
    add_log(f"Wachten tot de volgende candle: {seconds_to_next_candle} seconden...")
    time.sleep(seconds_to_next_candle)


def get_available_balance(asset):
    """Haal de spot account balans op"""
    try:
        # Haal de balans op voor de spot account
        balance = exchange.fetch_balance({'type': 'spot'})  # Haal de spot account balans op
        available_balance = balance['free'].get(asset, 0)  # Verkrijg het beschikbare saldo
        return available_balance
    except Exception as e:
        add_log(f"Fout bij het ophalen van de balans: {e}")
        return None


def fetch_data(symbol, timeframe, limit=49, retries=3, delay=5):
    """Haalt markthistorie op met verbeterde foutafhandeling"""
    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not candles:  # Controleer of er geen gegevens zijn opgehaald
                add_log("Geen gegevens ontvangen van de API.")
                return None
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # Controleer of de laatste candle volledig is
            last_candle_time = df.iloc[-1]["timestamp"]
            current_time = datetime.now()
            if (current_time - last_candle_time).seconds < 30 * 60:
                add_log("De laatste candle is nog niet volledig.")
                return None
            
            return df
        except ccxt.NetworkError as e:
            add_log(f"Netwerkfout bij ophalen van data: {e}")
        except ccxt.ExchangeError as e:
            add_log(f"Fout bij het ophalen van data van de exchange: {e}")
        except Exception as e:
            add_log(f"Onverwachte fout: {e}")
        
        # Wacht en probeer opnieuw na een mislukte poging
        add_log(f"Probeer het opnieuw na {delay} seconden...")
        time.sleep(delay)
    add_log("Maximale pogingen bereikt. Geen data ontvangen.")
    return None


def calculate_ema(data, period=10):
    """Bereken EMA op sluitprijzen"""
    ema = EMAIndicator(data["close"], window=period)
    data["ema10"] = ema.ema_indicator()
    return data

def place_order(side, symbol, amount):
    """Plaats een marktorder"""
    add_log(f"{side} order voor {amount} {symbol}")
    try:
        order = exchange.create_market_order(symbol, side, amount)
        add_log(f"Order geplaatst: {side} {amount} {symbol}")
        return order
    except Exception as e:
        add_log(f"Fout bij het plaatsen van een order: {e}")
        return None

def get_open_position(symbol):
    """Controleer of er een open positie is."""
    try:
        positions = exchange.fetch_positions()
        for position in positions:
            if position["symbol"] == symbol and float(position["contracts"]) > 0:
                return position
        return None
    except Exception as e:
        add_log(f"Fout bij ophalen van positie: {e}")
        return None

def close_position(position):
    """Sluit een bestaande positie."""
    try:
        side = "sell" if position["side"] == "buy" else "buy"
        amount = position["amount"]
        exchange.create_market_order(SYMBOL, side, amount)
        add_log(f"Positie gesloten: {side} {amount} {SYMBOL}")
    except Exception as e:
        add_log(f"Fout bij sluiten van positie: {e}")

def main():
    current_position = None

    while True:
        try:
            # Wacht tot het begin van de volgende candle
            wait_until_next_candle(interval_minutes=15)
            add_log(f"Candle tijd: {datetime.now()}")

            # Data ophalen
            data = fetch_data(SYMBOL, TIMEFRAME)
            if data is None:
                add_log("Geen gegevens ontvangen, opnieuw proberen.")
                continue  # Herstart de loop als er geen gegevens zijn
            data = calculate_ema(data)

            # Controleer laatste candle
            last_candle = data.iloc[-2]
            previous_candle = data.iloc[-3]

            add_log(f"Candle was onder en nu sluit boven ema10: "
                    f"{previous_candle['close'] < previous_candle['ema10'] and last_candle['close'] > last_candle['ema10']}")
            add_log(f"Candle was boven en nu sluit onder ema10: "
                    f"{previous_candle['close'] > previous_candle['ema10'] and last_candle['close'] < last_candle['ema10']}")
            add_log(f"{previous_candle['close']} is lager dan {previous_candle['ema10']}, "
                    f"en {last_candle['close']} is hoger dan {last_candle['ema10']}")
            add_log(f"{previous_candle['close']} is hoger dan {previous_candle['ema10']}, "
                    f"en {last_candle['close']} is lager dan {last_candle['ema10']}")

            # Koop bij bullish crossover (prijs sluit boven ema10)
            if previous_candle["close"] < previous_candle["ema10"] and last_candle["close"] > last_candle["ema10"]:
                available_balance = get_available_balance(TRADE_ASSET)
                if available_balance > 2:  # Zorg ervoor dat je voldoende USDT hebt om te kopen
                    amount_to_buy = available_balance / last_candle["close"]  # Bereken hoeveel ADA je kunt kopen
                    place_order("buy", SYMBOL, amount_to_buy)
                    add_log(f"Gekocht {amount_to_buy} ADA voor {available_balance} USDT.")

            # Verkoop bij bearish crossover (prijs sluit onder ema10)
            elif previous_candle["close"] > previous_candle["ema10"] and last_candle["close"] < last_candle["ema10"]:
                available_balance = get_available_balance("ADA")
                add_log(f"Beschikbaar saldo ADA: {available_balance}")
                if available_balance > 0:
                    place_order("sell", SYMBOL, available_balance)  # Verkoop de volledige ADA positie
                    add_log(f"Verkocht {available_balance} ADA voor USDT vanwege ema10 verandering.")

        except Exception as e:
            add_log(f"Fout in de hoofdloop: {e}")
            time.sleep(60)


# Draai de bot in een aparte thread
def run_bot():
    main()


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    app.run(host="0.0.0.0", port=5000)  # Start de Flask-server
