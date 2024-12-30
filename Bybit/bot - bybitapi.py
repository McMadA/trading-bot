import ccxt
import pandas as pd
from ta.trend import EMAIndicator
import time
from datetime import datetime, timedelta
import math
from pybit.unified_trading import HTTP
import time

#v1.1
# Configuratie
API_KEY = "vyq7FtlXm1CEbjL17s"
API_SECRET = "fv5622xa4q5IH7zQdqDyXh1JJO84sNFUy4Aq"
SYMBOL = "ADAUSDT"  # Pas aan naar jouw gewenste handelspaar
TIMEFRAME = "15m"  # Tijdframe van candles
TRADE_ASSET = "USDT"  # Gebruik de beschikbare USDT voor de order
TRADE_COIN = "ADA"  # Gebruik de beschikbare ADA voor de order
LEVERAGE = "10"

# Verbind met bybit
exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "margin"},  
})

# Initialize Bybit session
session = HTTP(
    testnet=False,  # Set to False if you're using the mainnet
    api_key=API_KEY,
    api_secret=API_SECRET,
)


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
            symbol= SYMBOL,
            tradeMode=0,
            buyLeverage= LEVERAGE,
            sellLeverage= LEVERAGE,
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
            leverage= LEVERAGE
        )
        print(f"Leverage set successfully: {response}")
        return response
    except Exception as e:
        print(f"Error setting leverage: {e}")


# def get_available_balance(asset):
#     """Haal de margin account balans op"""
#     try:
#         # Haal de balans op voor de spot account
#         balance = exchange.fetch_balance({'type': 'margin'})  # Haal de margin account balans op
#         available_balance = balance['free'].get(asset, 0)  # Verkrijg het beschikbare saldo
#         return available_balance
#     except Exception as e:
#         print(f"Fout bij het ophalen van de balans: {e}")
#         return None


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


def place_order(symbol, amount, side):
    """Place a market order to go long."""
    print(f"Placing a long order for {amount} {symbol}.")
    try:
        params = {
            "symbol": symbol.replace("/", ""),  # Convert to Bybit's symbol format, e.g., ADAUSDT
            "side": side,  # 'Buy' for long orders
            "orderType": "Market",  # Market order
            "qty": amount,  # Quantity to buy
            "category": "linear",  # Assuming linear contract (use "spot" if trading spot markets)
            "isLeverage": 1,
        }
        response = session.place_order(**params)
        print(f"Order successfully placed: {response}")
        return response
    except Exception as e:
        print(f"Error bij plaatsen van een order: {e}")
        return None


def main():
    # set_position_mode()
    
    # Stel leverage in voor het symbool (Isolated Margin)
    toggle_margin_trade()
    set_leverage()
    toggle_margin_trade()

    data = fetch_data(SYMBOL, TIMEFRAME)
    last_candle = data.iloc[-1]
    print(last_candle)

    available_balance = get_available_balance(TRADE_ASSET) #Hoeveelheid USDT
    print("balans = ", available_balance, TRADE_ASSET)

    if available_balance is None or available_balance <= 0:
        print("Onvoldoende balans.")
        return  # Exit if balance retrieval fails or is insufficient

    amount_to_buy = available_balance / last_candle["close"]  # Default assignment if no position to close
    afgerond_getal = math.floor(amount_to_buy)

    if afgerond_getal > 0:
        # place_order(SYMBOL, afgerond_getal, "Buy")
        print(f"Gekocht {afgerond_getal} ADA voor {available_balance} USDT.")
    else:
        print("Geen kooporder geplaatst, bedrag om te kopen is te klein of nul.")


if __name__ == "__main__":
    main()