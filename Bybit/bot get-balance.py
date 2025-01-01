import ccxt

API_KEY = ''
API_SECRET = ''

# Gebruik de juiste ByBit API-URL voor de v5 API
API_URL = 'https://api.bybit.nl'

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "margin"},  
})


def get_available_balance(asset):
    """Haal de margin account balans op"""
    try:
        # Haal de balans op voor de spot account
        balance = exchange.fetch_balance({'type': 'margin'})  # Haal de margin account balans op
        available_balance = balance['free'].get(asset, 0)  # Verkrijg het beschikbare saldo
        return available_balance
    except Exception as e:
        print(f"Fout bij het ophalen van de balans: {e}")
        return None

def main():
    
        # Verkrijg de margin account balans
    print(f"Beschikbaar: {get_available_balance('ADA')}")

if __name__ == "__main__":
    main()
