import ccxt

# Configuratie
API_KEY = ""  # Vervang door je eigen API-sleutel
API_SECRET = ""  # Vervang door je eigen API-secret

# Verbind met MEXC
exchange = ccxt.mexc({
    "apiKey": API_KEY,
    "secret": API_SECRET,
})

def get_spot_balance():
    """Haal de spot account balans op"""
    try:
        # Haal de balans op voor de spot account
        balance = exchange.fetch_balance({'type': 'spot'})  # Haal de spot account balans op
        return balance
    except Exception as e:
        print(f"Fout bij het ophalen van de balans: {e}")
        return None

def main():
    try:
        # Verkrijg de spot account balans
        balance = get_spot_balance()
        if balance:
            print("Spot Account Balans:")
            for asset, info in balance['total'].items():
                print(f"{asset}: {info}")
        else:
            print("Kan de balans niet ophalen.")
    except Exception as e:
        print(f"Fout in de hoofdloop: {e}")

if __name__ == "__main__":
    main()
