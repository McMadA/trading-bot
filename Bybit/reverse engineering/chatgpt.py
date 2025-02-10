import ccxt
import pandas as pd
from ta.trend import EMAIndicator, SMAIndicator
import time
from datetime import datetime

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

# Functies voor data ophalen en indicatoren
def fetch_data(symbol, timeframe, limit=1000, retries=3, delay=5):    
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

def calculate_sma(data, period=20):
    sma = SMAIndicator(data["close"], window=period)
    data["sma"] = sma.sma_indicator()
    return data

def calculate_ema(data, period=10):
    """Bereken EMA's op sluitprijzen"""
    ema = EMAIndicator(data["close"], window=period)
    data["ema"] = ema.ema_indicator()
    return data

def buy_order(amount):
    """Simuleer een kooporder"""
    print(f"Kooporder geplaatst voor {amount} {SYMBOL}")
    return amount  # Retourneer het aantal gekochte eenheden

def sell_order(amount):
    """Simuleer een verkooporder"""
    print(f"Verkooporder geplaatst voor {amount} {SYMBOL}")
    return amount  # Retourneer het aantal verkochte eenheden

def simulate_trading(data, start_balance=100, buy_amount=100):
    """Simuleer trading op basis van EMA en SMA"""
    balance = start_balance
    position = 0  # Aantal ADA gekocht
    last_buy_price = 0
    last_sell_price = 0

    for i in range(20, len(data)):  # Start vanaf de 20e candle (waar de SMA20 beschikbaar is)
        current_ema = data.iloc[i]["ema"]
        current_sma = data.iloc[i]["sma"]
        close_price = data.iloc[i]["close"]
        
        # Koop wanneer EMA boven SMA komt
        if current_ema > current_sma and position == 0:
            position = buy_order(buy_amount / close_price)  # Aantal gekocht
            last_buy_price = close_price
            print(f"Gekocht: {position} eenheden van {SYMBOL} tegen {close_price} USD")
        
        # Verkoop wanneer EMA onder SMA komt
        elif current_ema < current_sma and position > 0:
            balance += position * close_price  # Verkoop alle posities
            last_sell_price = close_price
            print(f"Verkocht: {position} eenheden van {SYMBOL} tegen {close_price} USD")
            position = 0  # Geen open positie meer

    # Eindresultaat
    if position > 0:  # Als er nog een open positie is aan het eind
        balance += position * data.iloc[-1]["close"]
        print(f"Verkocht aan het einde: {position} eenheden van {SYMBOL} tegen {data.iloc[-1]['close']} USD")

    print(f"Eindbalans: {balance} USDT")
    return balance

def main():
    # Data ophalen
    data = fetch_data(SYMBOL, TIMEFRAME)
    if data is None:
        print("Geen gegevens ontvangen, opnieuw proberen.")
        return
    data = calculate_ema(data)
    data = calculate_sma(data)

    # Simuleer het handelen
    final_balance = simulate_trading(data)
    print(f"Resultaat van de simulatie: {final_balance} USDT")

if __name__ == "__main__":
    main()
