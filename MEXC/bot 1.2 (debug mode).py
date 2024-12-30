import ccxt
import pandas as pd
from ta.trend import SMAIndicator
import time
from datetime import datetime, timedelta

# Configuratie
API_KEY = ""
API_SECRET = ""
SYMBOL = "ADA/USDT"  # Pas aan naar jouw gewenste handelspaar
TIMEFRAME = "5m"  # Tijdframe van candles
TRADE_ASSET = "USDT"  # Gebruik de beschikbare USDT voor de order

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},  
})

def wait_until_next_candle(interval_minutes=5):
    """Wacht tot het begin van de volgende candle op een specifiek interval."""
    now = datetime.now()
    # Bereken het aantal seconden tot het volgende interval
    seconds_to_next_candle = (
        interval_minutes * 60 - (now.minute % interval_minutes) * 60 - now.second
    )
    print(f"Wachten tot de volgende candle: {seconds_to_next_candle} seconden...")
    time.sleep(seconds_to_next_candle)


def get_available_balance(asset):
    """Haal de spot account balans op"""
    try:
        # Haal de balans op voor de spot account
        balance = exchange.fetch_balance({'type': 'spot'})  # Haal de spot account balans op
        available_balance = balance['free'].get(asset, 0)  # Verkrijg het beschikbare saldo
        return available_balance
    except Exception as e:
        print(f"Fout bij het ophalen van de balans: {e}")
        return None


def fetch_data(symbol, timeframe, limit=49, retries=3, delay=5):
    """Haalt markthistorie op met verbeterde foutafhandeling"""
    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not candles:  # Controleer of er geen gegevens zijn opgehaald
                print("Geen gegevens ontvangen van de API.")
                return None
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df
        except ccxt.NetworkError as e:
            print(f"Netwerkfout bij ophalen van data: {e}")
        except ccxt.ExchangeError as e:
            print(f"Fout bij het ophalen van data van de exchange: {e}")
        except Exception as e:
            print(f"Onverwachte fout: {e}")
        
        # Wacht en probeer opnieuw na een mislukte poging
        print(f"Probeer het opnieuw na {delay} seconden...")
        time.sleep(delay)
    print("Maximale pogingen bereikt. Geen data ontvangen.")
    return None



def calculate_sma(data, period=20):
    """Bereken SMA op sluitprijzen"""
    sma = SMAIndicator(data["close"], window=period)
    data["sma20"] = sma.sma_indicator()
    return data

def place_order(side, symbol, amount):
    """Plaats een marktorder"""
    print(side, symbol, amount)
    try:
        order = exchange.create_market_order(symbol, side, amount)
        print(f"Order geplaatst: {side} {amount} {symbol}")
        return order
    except Exception as e:
        print(f"Fout bij het plaatsen van een order: {e}")
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
        print(f"Fout bij ophalen van positie: {e}")
        return None

def close_position(position):
    """Sluit een bestaande positie."""
    try:
        side = "sell" if position["side"] == "buy" else "buy"
        amount = position["amount"]
        exchange.create_market_order(SYMBOL, side, amount)
        print(f"Positie gesloten: {side} {amount} {SYMBOL}")
    except Exception as e:
        print(f"Fout bij sluiten van positie: {e}")

def main():
    current_position = None

    while True:
        try:
            # Wacht tot het begin van de volgende candle
            
            wait_until_next_candle(interval_minutes=5)
            print(datetime.now())

            # Data ophalen
            data = fetch_data(SYMBOL, TIMEFRAME)
            if data is None:
                print("Geen gegevens ontvangen, opnieuw proberen.")
                continue  # Herstart de loop als er geen gegevens zijn
            data = calculate_sma(data)
            

            # Controleer laatste candle
            last_candle = data.iloc[-1]
            previous_candle = data.iloc[-2]

            print("Candle was onder en nu sluit boven SMA20   ",previous_candle["close"] < previous_candle["sma20"] and last_candle["close"] > last_candle["sma20"])
            print("Candle was boven en nu sluit onder SMA20   ",previous_candle["close"] > previous_candle["sma20"] and last_candle["close"] < last_candle["sma20"])


            # Koop bij bullish crossover (prijs sluit boven SMA20)
            if previous_candle["close"] < previous_candle["sma20"] and last_candle["close"] > last_candle["sma20"]:
                available_balance = get_available_balance(TRADE_ASSET)
                if available_balance > 2:  # Zorg ervoor dat je voldoende USDT hebt om te kopen
                    amount_to_buy = available_balance / last_candle["close"]  # Bereken hoeveel ADA je kunt kopen
                    place_order("buy", SYMBOL, amount_to_buy)
                    print(f"Gekocht {amount_to_buy} ADA voor {available_balance} USDT.")

            # Verkoop bij bearish crossover (prijs sluit onder SMA20)
            elif previous_candle["close"] > previous_candle["sma20"] and last_candle["close"] < last_candle["sma20"]:
                # Hier moet je de hoeveelheid ADA die je hebt verkopen
                available_balance = get_available_balance("ADA")
                print(available_balance)
                if available_balance > 0:
                    place_order("sell", SYMBOL, available_balance)  # Verkoop de volledige ADA positie
                    print(f"Verkocht {available_balance} ADA voor USDT vanwege SMA20 verandering.")
                    

        except Exception as e:
            print(f"Fout in de hoofdloop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

