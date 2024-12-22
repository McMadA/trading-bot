import ccxt

# Configuratie
API_KEY = ""  # Vervang door je eigen API-sleutel
API_SECRET = ""  # Vervang door je eigen API-secret
SYMBOL = "ADA/USDT"  # Het handelspaar
LOT_SIZE = 0  # Hoeveelheid crypto om te handelen

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "future"},  # Activeer futures trading
})

def place_order(side, symbol, amount):
    """Plaats een marktorder"""
    try:
        order = exchange.create_market_order(symbol, side, amount)
        print(f"Order geplaatst: {side} {amount} {symbol}")
        return order
    except Exception as e:
        print(f"Fout bij het plaatsen van een order: {e}")
        return None

def main():
    try:
        # Plaats onmiddellijk een kooporder (buy) of verkooporder (sell)
        side = "buy"  # Of "sell" afhankelijk van de richting van de handel
        current_position = place_order(side, SYMBOL, LOT_SIZE)
    except Exception as e:
        print(f"Fout in de hoofdloop: {e}")

if __name__ == "__main__":
    main()

