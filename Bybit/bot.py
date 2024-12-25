# import requests
# import time
# import hashlib

# # Voeg je ByBit API-sleutel en geheime sleutel toe
# API_KEY = '5DNOpd7WcfckW8oF7g'
# API_SECRET = 'EI4JCUVohmBrIln8Q7TdPjSo7zVFON2vAvyl'

# # Gebruik de juiste ByBit API-URL voor de v5 API
# API_URL = 'https://api.bybit.nl'


# # Parameters voor de kandelaren
# symbol = "ADAUSDT"
# interval = "1"  # 1 minuut, je kunt andere intervallen gebruiken zoals "5", "15", "30", "60", etc.
# limit = 50  # Aantal candles dat we willen ophalen

# # Functie om de handtekening te maken voor API-aanroepen
# def generate_signature(params, api_secret):
#     param_str = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
#     return hashlib.sha256(f"{param_str}{api_secret}".encode('utf-8')).hexdigest()

# # Functie om de laatste 50 candles op te halen
# def get_last_50_candle_closes(symbol, interval, limit=50):
#     params = {
#         'api_key': API_KEY,
#         'symbol': symbol,
#         'interval': interval,  # Interval (bijv. 1m, 5m, 1h)
#         'limit': limit,
#         'timestamp': int(time.time() * 1000),
#     }
#     params['sign'] = generate_signature(params, API_SECRET)

#     # Maak de API-aanroep
#     response = requests.get(f"{API_URL}/v2/public/kline/list", params=params)
    
#     # Controleer of de aanvraag succesvol was
#     if response.status_code == 200:
#         data = response.json()
#         if data['ret_code'] == 0:
#             closes = [item['close'] for item in data['result']]
#             return closes
#         else:
#             print(f"API-fout: {data['ret_msg']}")
#             return []
#     else:
#         print(f"Fout bij API-aanroep: {response.status_code}")
#         print(f"Respons: {response.text}")
#         return []

# # Haal de laatste 50 sluitingsprijzen op
# closes = get_last_50_candle_closes(symbol, interval)

# if closes:
#     print("Laatste 50 sluitingsprijzen:")
#     print(closes)
# else:
#     print("Geen gegevens opgehaald.")

import requests
import time

# Gebruik de juiste ByBit API-URL voor v5
API_URL = 'https://api.bybit.com/v5/market/candles'

# Parameters voor de kandelaren
symbol = "ADAUSDT"
interval = "1"  # 1 minuut, je kunt andere intervallen gebruiken zoals "5", "15", "30", "60", etc.
limit = 50  # Aantal candles dat we willen ophalen

# Functie om de laatste 50 candles op te halen
def get_last_50_candle_closes(symbol, interval, limit=50):
    params = {
        'symbol': symbol,
        'interval': interval,  # Interval (bijv. 1m, 5m, 1h)
        'limit': limit,
        'api_key': 'JOUW_API_KEY',  # Voeg je API-sleutel toe als dat nodig is
        'timestamp': int(time.time() * 1000),
    }

    # Maak de API-aanroep
    response = requests.get(API_URL, params=params)
    
    # Controleer of de aanvraag succesvol was
    if response.status_code == 200:
        data = response.json()
        if data.get('ret_code') == 0:
            closes = [item['close'] for item in data['result']]
            return closes
        else:
            print(f"API-fout: {data.get('ret_msg')}")
            return []
    else:
        print(f"Fout bij API-aanroep: {response.status_code}")
        print(f"Respons: {response.text}")
        return []

# Haal de laatste 50 sluitingsprijzen op
closes = get_last_50_candle_closes(symbol, interval)

if closes:
    print("Laatste 50 sluitingsprijzen:")
    print(closes)
else:
    print("Geen gegevens opgehaald.")

