import ccxt

# Configuratie
API_KEY = ""  # Vervang door je eigen API-sleutel
API_SECRET = ""  # Vervang door je eigen API-secret
LOT_SIZE = 2  # Hoeveelheid crypto om te handelen
LEVERAGE = 5  # Hefboomwerking voor futures trading
symbol = "ADAUSDT"  # Symbool van het handelspaar
side = "BUY"

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"type": "future", },  # Activeer futures trading
})

market = {
    "id": "adausdt",  
    "symbol": "ADA/USDT",
    "base": "ADA",
    "quote": "USDT",
    "active": True,
    "type": "future",
    "future": True,
    "spot": False,
}

def set_leverage(leverage):
    """Set the leverage for the trading account."""
    print(f"Setting leverage to {LEVERAGE}x.")
    try:
        params =  {
            "openType": 1,  # 1 for isolated margin, 2 for cross margin
            "positionType": 1,  # 1 for long position, 2 for short position
        }
        response = exchange.setLeverage(leverage, "ADA/USDT:USDT", params)
        print(f"Leverage successfully set: {response}")
        return response
    except Exception as e:
        print(f"Error setting leverage: {e}")
        return None

def place_order(side, symbol, amount):
    """Place a market order to go long."""
    print(f"Placing a long order for {amount} {symbol}.")
    try:
        params = {
            "side": side,  # 'Buy' for long orders
            "orderType": "Market",  # Market order
            "qty": amount,  # Quantity to buy
            "category": "linear",  # Assuming linear contract (use "spot" if trading spot markets)
            "isLeverage": 1,
        }
        response = exchange.createOrder(symbol, "market", side, amount, None, params)
        print(f"Order successfully placed: {response}")
        return response
    except Exception as e:
        print(f"Error bij plaatsen van een order: {e}")
        return None

def main():
    print(market)
    set_leverage()
    try:
        # Plaats onmiddellijk een kooporder (buy) of verkooporder (sell)
        place_order(side, symbol, LOT_SIZE)
    except Exception as e:
        print(f"Fout in de hoofdloop: {e}")

if __name__ == "__main__":
    main()

