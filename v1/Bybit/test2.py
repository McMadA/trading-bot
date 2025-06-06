import ccxt
from pybit.unified_trading import HTTP
from datetime import datetime
import pandas as pd
import time
from ta.trend import EMAIndicator, SMAIndicator


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
type = "market"
amount = 40
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

def calculate_sma(data, period=9):
    sma = SMAIndicator(data["close"], window=period)
    data["sma"] = sma.sma_indicator()
    return data
def calculate_ema(data, short_period=20, long_period=50):
    """Bereken EMA's op sluitprijzen"""
    ema_short = EMAIndicator(data["close"], window=short_period)
    ema_long = EMAIndicator(data["close"], window=long_period)

    data["ema20"] = ema_short.ema_indicator()
    data["ema50"] = ema_long.ema_indicator()
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
    print(f"Sluiten van {side} positie ...")
    try:
        params= {"reduceOnly": True,
                 "isLeverage": "1"}

        order = exchange.create_order(symbol, type, side, amount, price, params)
        print(f"Positie gesloten:  {amount} {symbol}")
        return order
    except Exception as e:
        print(f"Fout bij sluiten van positie: {e}")

def spot_margin_trade_get_vip_margin_data():
    """Haal VIP-margegegevens op voor een specifieke coin (ADA)."""
    try:
        # Haal de volledige gegevens op via de API
        response = session.spot_margin_trade_get_vip_margin_data()
        
        # Controleer of de response succesvol is
        if not response or response.get("retCode") != 0:
            print(f"Fout bij het ophalen van data: {response.get('retMsg', 'Onbekende fout')}")
            return None
        
        # Vind de lijst met coins
        vip_coin_list = response.get("result", {}).get("vipCoinList", [])
        if not vip_coin_list:
            print("Geen vipCoinList gevonden in de response.")
            return None
        
        # Doorzoek de 'list' voor de specifieke coin ADA
        for vip_level in vip_coin_list:
            coin_list = vip_level.get("list", [])
            ada_data = next(
                (item for item in coin_list if item.get("currency") == "USDT"),
                None
            )
            if ada_data:
                print(f"VIP-margegegevens voor ADA: {ada_data}")
                return ada_data
        
        print("ADA niet gevonden in de opgehaalde data.")
        return None
    except Exception as e:
        print(f"Fout bij het ophalen van VIP-margegegevens: {e}")
        return None



def main():
    # spot_margin_trade_get_vip_margin_data()
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
            data = calculate_sma(data)

            previous_candle = data.iloc[-1]
            previous2_candle = data.iloc[-2]

            print(f"Een-na-laatste candle: EMA20={previous2_candle['ema20']}, SMA={previous2_candle['sma']}")
            print(f"Laatste candle: EMA20={previous_candle['ema20']}, SMA={previous_candle['sma']}")

            if previous_candle["ema20"] > previous_candle["sma"]:
                print("Trend: EMA20 boven SMA")
            elif previous_candle["ema20"] < previous_candle["sma"]:
                print("Trend: EMA20 onder SMA") 

            print ("-------------------")

            if previous2_candle["ema20"] < previous2_candle["sma"] and previous_candle["ema20"] > previous_candle["sma"]:
                print("SMA komt onder EMA: Verkoop signaal")
                # Plaats een kooporder indien nodig
                if current_position == "buy":
                    close_position("sell")
                create_order("sell")
                current_position = "sell"

            elif previous2_candle["ema20"] > previous2_candle["sma"] and previous_candle["ema20"] < previous_candle["sma"]:
                print("SMA komt boven EMA: Koop signaal")
                # Plaats een verkooporder indien nodig
                if current_position == "sell":
                    close_position("buy")
                create_order("buy")
                current_position = "buy"

            else:
                print("Geen signaal")
            
        except Exception as e:
            print(f"Fout bij het ophalen van data: {e}")
            print(f"Probeer het opnieuw na 5 seconden...")
            time.sleep(5)
            continue

if __name__ == "__main__":
    main()
