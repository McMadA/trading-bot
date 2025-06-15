# Python file for getting dataset from free Binance API
import pandas as pd
from binance.client import Client
from binance.enums import *
def get_binance_data(symbol, interval, start_date, end_date):
    """
    Fetch historical klines data from Binance API.

    :param symbol: Trading pair symbol (e.g., 'BTCUSDT').
    :param interval: Kline interval (e.g., Client.KLINE_INTERVAL_1MINUTE).
    :param start_date: Start date in 'YYYY-MM-DD' format.
    :param end_date: End date in 'YYYY-MM-DD' format.
    :return: DataFrame containing the klines data.
    """
    client = Client()
    klines = client.get_historical_klines(symbol, interval, start_date, end_date)
    
    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])
    
    # Convert timestamps to datetime
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    
    # Set index to Open time
    df.set_index('Open time', inplace=True)
    
    return df

# display the first few rows of the dataset
print(get_binance_data('BTCUSDT', Client.KLINE_INTERVAL_1MINUTE, '2023-01-01', '2023-01-02').head())



# ------------------------------------------------------------------------------------------------------------


# Python file for getting latest prices from bitcoin coins from free Binance API using CCXT
import ccxt
def get_latest_prices(symbols):
    """
    Fetch the latest prices for a list of symbols from Binance.

    :param symbols: List of trading pair symbols (e.g., ['BTC/USDT', 'ETH/USDT']).
    :return: Dictionary with symbols as keys and their latest prices as values.
    """
    binance = ccxt.binance()
    ticker = binance.fetch_tickers(symbols)
    
    # Extract the latest prices
    latest_prices = {symbol: ticker[symbol]['last'] for symbol in symbols if symbol in ticker}
    
    return latest_prices

  
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
prices = get_latest_prices(symbols)
print(prices)

    
