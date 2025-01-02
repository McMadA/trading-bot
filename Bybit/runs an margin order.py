import ccxt
from pybit.unified_trading import HTTP






API_KEY = "8JipCzXe9HTR6IRQC8"
API_SECRET = "xaH4j3bL3KPUkUdUjTTWRY6l3lS4XLUQ57oh"

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
})
session = HTTP(
    testnet=False,  # Set to False if you're using the mainnet
    api_key=API_KEY,
    api_secret=API_SECRET,
)

symbol = "ADA/USDT"
type = "market"
amount = 2
price = 1.0
leverage = 10



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

def create_order(side):
    """Plaats een marktorder"""
    print(f"{side} order voor {amount} {symbol}")
    try:
        params = {
            "isLeverage": "1"
        }
        order = exchange.create_order(symbol, type, side, amount, price, params)
        print(f"Order geplaatst {symbol, type, side, amount, price, params}")
        return order
    except Exception as e:
        print(f"Fout bij het plaatsen van een order: {e}")
        return None


def main():
    toggle_margin_trade()
    switch_cross_isolated_mode()
    set_leverage()





    create_order("sell")

if __name__ == "__main__":
    main()