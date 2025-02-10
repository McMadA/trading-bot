import ccxt

API_KEY = '8JipCzXe9HTR6IRQC8'
API_SECRET = 'xaH4j3bL3KPUkUdUjTTWRY6l3lS4XLUQ57oh'

# Gebruik de juiste ByBit API-URL voor de v5 API
API_URL = 'https://api.bybit.nl'

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "options": {"defaultType": "margin"},  
})


def get_available_balance():
    """Haal de margin account balans op"""
    try:
        # Haal de balans op voor de spot account
        balance = exchange.fetch_balance({'type': 'margin'})  # Haal de margin account balans op
        return balance
    except Exception as e:
        print(f"Fout bij het ophalen van de balans: {e}")
        return None

def main():
    
        # Verkrijg de margin account balans
    print(f"Beschikbaar: {get_available_balance()}")

if __name__ == "__main__":
    main()
