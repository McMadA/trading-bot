import ccxt
import pandas as pd
from ta.trend import EMAIndicator
import time
from datetime import datetime

#v1.1
# Configuratie
API_KEY = "8JipCzXe9HTR6IRQC8"
API_SECRET = "xaH4j3bL3KPUkUdUjTTWRY6l3lS4XLUQ57oh"
SYMBOL = "ADA/USDT"  # Pas aan naar jouw gewenste handelspaar
TIMEFRAME = "15m"  # Tijdframe van candles
TRADE_ASSET = "USDT"  # Gebruik de beschikbare USDT voor de order

# Verbind met MEXC
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "spot"},  
})


def fetch_data(symbol, timeframe, limit=52, retries=3, delay=5):    
    """Haalt markthistorie op met verbeterde foutafhandeling"""
    for attempt in range(retries):
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not candles:  # Controleer of er geen gegevens zijn opgehaald
                print("Geen gegevens ontvangen van de API.")
                return None
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # Controleer of de laatste candle volledig is
            last_candle_time = df.iloc[-1]["timestamp"]
            current_time = datetime.now()
            if (current_time - last_candle_time).seconds < 30 * 60:
                print("De laatste candle is nog niet volledig.")
                return None
            
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


def main():
    # Data ophalen
    data = fetch_data(SYMBOL, TIMEFRAME)
    if data is None:
        print("Geen gegevens ontvangen, opnieuw proberen.")
    print(data)

if __name__ == "__main__":
    main()
