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


def get_margin_balance():
    """Haal de margin account balans op"""
    try:
        # Haal de balans op voor de margin account
        balance = exchange.fetch_balance({'type': 'margin'})  # Haal de margin account balans op
        return balance
    except Exception as e:
        print(f"Fout bij het ophalen van de balans: {e}")
        return None

def main():
    try:
        # Verkrijg de margin account balans
        balance = get_margin_balance()
        if balance:
            print("margin Account Balans:")
            for asset, info in balance['total'].items():
                print(f"{asset}: {info}")
        else:
            print("Kan de balans niet ophalen.")
    except Exception as e:
        print(f"Fout in de hoofdloop: {e}")

if __name__ == "__main__":
    main()
