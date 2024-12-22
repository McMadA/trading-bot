# README voor de Handelsbot

Dit project is een eenvoudige handelsbot geschreven in Python die gebruik maakt van de `ccxt` bibliotheek om te handelen op de MEXC exchange. De bot maakt gebruik van de Simple Moving Average (SMA) strategie om koop- en verkoopbeslissingen te nemen voor de ADA/USDT handelspaar. Op moment wordt de 5m timeframe gebruikt in de code.

## Inhoud

1. [Vereisten](#vereisten)
2. [Configuratie](#configuratie)
3. [Functies](#functies)
4. [Gebruik](#gebruik)
5. [Belangrijke opmerking](#belangrijke-opmerking)

## Vereisten

- Python 3.x
- ccxt bibliotheek: Installeer met `pip install ccxt`
- ta bibliotheek: Installeer met `pip install ta`
- pandas bibliotheek: Installeer met `pip install pandas`

## Configuratie

Voor je de bot kunt gebruiken, moet je de volgende configuratie-instellingen aanpassen in de code:

```python
API_KEY = "jouw_api_key"
API_SECRET = "jouw_api_secret"
SYMBOL = "ADA/USDT"  # Handels paar
TIMEFRAME = "5m"     # Tijdframe voor de candles
TRADE_ASSET = "USDT" # Valuta voor handelen
```

Zorg ervoor dat je een API-sleutel en geheime sleutel hebt aangemaakt op de MEXC exchange en dat deze de juiste machtigingen heeft voor handel.

## Functies

- **wait_until_next_candle**: Wacht tot de volgende candle begint.
- **get_available_balance**: Haalt het beschikbare saldo op voor een specifieke asset.
- **fetch_data**: Haalt OHLCV (Open, High, Low, Close, Volume) gegevens op voor het opgegeven handels paar.
- **calculate_sma**: Bereken de Simple Moving Average (SMA) voor de sluitingsprijzen.
- **place_order**: Plaatst een marktorder om te kopen of verkopen.
- **main**: De hoofdlogica van de bot die de handelsbeslissingen neemt op basis van de SMA-strategie.

## Gebruik

Om de bot uit te voeren, kun je de volgende commandoregel gebruiken:

```bash
python jouw_bestand.py
```

Vervang `jouw_bestand.py` door de naam van je Python-bestand.

## Belangrijke opmerking

- Test de bot eerst in een demo-omgeving of met een klein bedrag voordat je deze in een live omgeving gebruikt.
- Zorg ervoor dat je de API-sleutels veilig opslaat en niet deelt met anderen.
- Wees je bewust van de risico's van handelen en investeer alleen wat je bereid bent te verliezen.

Dit is een basisversie van een handelsbot en kan verder worden uitgebreid met meer geavanceerde functies en strategieën.