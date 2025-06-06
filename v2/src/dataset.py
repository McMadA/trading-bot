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