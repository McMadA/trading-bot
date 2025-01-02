import ccxt
from pybit.unified_trading import HTTP
from datetime import datetime
import pandas as pd
import time
from ta.trend import EMAIndicator


API_KEY = ""
API_SECRET = ""

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
})
session = HTTP(
    testnet=False,  
    api_key=API_KEY,
    api_secret=API_SECRET,
)

symbol = "ADA/USDT"
timeframe = "15m"
type = "limit"
amount = 20
price = 1.0
leverage = 5


def wait_until_next_candle(interval_minutes=15):
    """Wacht tot het begin van de volgende candle op een specifiek interval."""
    now = datetime.now()
    # Bereken het aantal seconden tot het volgende interval
    seconds_to_next_candle = (
        interval_minutes * 60 - (now.minute % interval_minutes) * 60 - now.second
    )
    print(f"Wachten tot de volgende candle: {seconds_to_next_candle} seconden...")
    time.sleep(seconds_to_next_candle)
def toggle_margin_trade():
    """Toggle margin trading mode on Bybit."""
    try:
        response = session.spot_margin_trade_toggle_margin_trade(
            spotMarginMode= "1",   # Enable margin trading
        )
        print(f"Margin trading mode set successfully: {response}")
        return response
    except Exception as e:
        print(f"Error setting margin trading mode: {e}")
def switch_cross_isolated_mode():
    """Switch between cross and isolated margin mode."""
    try:
        response = session.switch_margin_mode(
            category= "linear",
            symbol= symbol,
            tradeMode=0,
            buyLeverage= leverage,
            sellLeverage= leverage,
        )
        print(f"Margin mode set successfully: {response}")
        return response
    except Exception as e:
        print(f"Error setting margin mode: {e}")
def set_leverage():
    """
    Set leverage for Bybit trading using pybit.
    :param symbol: Trading symbol (e.g., "BTCUSDT")
    :param buyLeverage: Leverage for long positions
    :param sellLeverage: Leverage for short positions
    :param category: Market category (e.g., "spot")
    """
    try:
        response = session.spot_margin_trade_set_leverage(
            leverage= leverage
        )
        print(f"Leverage set successfully: {response}")
        return response
    except Exception as e:
        print(f"Error setting leverage: {e}")
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

def calculate_ema(data, period=10):
    """Bereken EMA op sluitprijzen"""
    ema = EMAIndicator(data["close"], window=period)
    data["ema10"] = ema.ema_indicator()
    return data

def create_order(side):
    """Plaats een marktorder"""
    print(f"{side} order voor {amount} {symbol}")
    try:
        params = {
            "reduceOnly": False,  
            "isLeverage": "1"
        }
        order = exchange.create_order(symbol, type, side, amount, price, params)
        print(f"Order geplaatst {symbol, type, side, amount, price, params}")
        return order
    except Exception as e:
        print(f"Fout bij het plaatsen van een order: {e}")
        return None


def close_position(side):
    """Sluit een bestaande positie."""
    opposite_side = "sell" if side == "buy" else "buy"
    print(f"Sluiten van {side} positie ...")
    try:
        params= {"reduceOnly": True}
        order = exchange.create_order(symbol, type, opposite_side, amount, price, params)
        print(f"Positie gesloten:  {amount} {symbol}")
        return order
    except Exception as e:
        print(f"Fout bij sluiten van positie: {e}")



def main():
    toggle_margin_trade()
    switch_cross_isolated_mode()
    set_leverage()
    current_position = None

    while True:
        try:
            wait_until_next_candle(interval_minutes=15)
            print(f"Candle tijd: {datetime.now()}")

            data = fetch_data(symbol, timeframe)
            if data is None:
                print("Geen gegevens ontvangen, opnieuw proberen.")
                continue
            data = calculate_ema(data)

            last_candle = data.iloc[-1]
            previous_candle = data.iloc[-2]
            previous2_candle = data.iloc[-3]
            previous3_candle = data.iloc[-4]
            previous4_candle = data.iloc[-5]
            previous5_candle = data.iloc[-6]
            previous6_candle = data.iloc[-7]

            print(f"Last candle close: {last_candle['close']}")
            print(f"Last candle ema10: {last_candle['ema10']}")
            print(f"Previous candle close: {previous_candle['close']}")
            print(f"Previous candle ema10: {previous_candle['ema10']}")
            print(f"Previous2 candle close: {previous2_candle['close']}")
            print(f"Previous2 candle ema10: {previous2_candle['ema10']}")
            print(f"Previous3 candle close: {previous3_candle['close']}")
            print(f"Previous3 candle ema10: {previous3_candle['ema10']}")
            print(f"Previous4 candle close: {previous4_candle['close']}")
            print(f"Previous4 candle ema10: {previous4_candle['ema10']}")
            print(f"Previous5 candle close: {previous5_candle['close']}")
            print(f"Previous5 candle ema10: {previous5_candle['ema10']}")
            print(f"Previous6 candle close: {previous6_candle['close']}")
            print(f"Previous6 candle ema10: {previous6_candle['ema10']}")


            print(f"Candle was onder en nu sluit boven ema10: "
                    f"{previous2_candle['close'] < previous2_candle['ema10'] and previous_candle['close'] > previous_candle['ema10']}")
            print(f"Candle was boven en nu sluit onder ema10: "
                    f"{previous2_candle['close'] > previous2_candle['ema10'] and previous_candle['close'] < previous_candle['ema10']}")


            print(f"{previous2_candle['close']} is lager dan {previous2_candle['ema10']}, "
                    f"en {previous_candle['close']} is hoger dan {previous_candle['ema10']}")
            print(f"{previous2_candle['close']} is hoger dan {previous2_candle['ema10']}, "
                    f"en {previous_candle['close']} is lager dan {previous_candle['ema10']}")
            #als candle sluit boven de ema10 vanaf onder dan kopen
            if previous2_candle["close"] < previous2_candle["ema10"] and previous_candle["close"] > previous_candle["ema10"]:
                print("Koop signaal")
                if current_position == "short":
                    close_position("short")
                create_order("buy")
                current_position = "long"

            elif previous2_candle["close"] > previous2_candle["ema10"] and previous_candle["close"] < previous_candle["ema10"]:
                print("Verkoop signaal")
                if current_position == "long":
                    close_position("long")
                create_order("sell")
                current_position = "short"

            else:
                print("Geen signaal")
            
        except Exception as e:
            print(f"Fout bij het ophalen van data: {e}")
            print(f"Probeer het opnieuw na 5 seconden...")
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
