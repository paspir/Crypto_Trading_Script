import os
from binance.client import Client
import time
import pandas as pd
import numpy as np
import talib
import ccxt

# Enter your API keys here
api_key = ''
api_secret = ''

# Create a Binance API client instance
client = Client(api_key, api_secret)

def get_latest_price(symbol):
    try:
        ticker = client.get_ticker(symbol=symbol)
        return float(ticker['lastPrice'])
    except:
        print(f"Failed to get latest price for {symbol}")
        return 0

# Replace with the symbol you want to trade (e.g. 'DOT/USDT')
symbol = 'DOT/USDT'


binance = ccxt.binance({
    'apiKey': 'eicglm4RUxDqaSssAA0W5suQmYqR1t8jbGxO1ehRCw97IGXE5tJTVQ8HUDAuEA0s',
    'secret': 'jjltOQJfgDkaoxWuKUnNYcWyjbGgIh1MKRh8fUgEYODzSpUyOTbpb9BAtPX9JA4o',
})


#Calculate Start time
start_time = time.time()



# Replace with the amount you want to invest per trade
investment_amount = 270

#Percentage of portfolio being used
percentageAtUse = 0.5

# Replace with the number of candles to use for the Bollinger Bands calculation
bb_period = 20

# Replace with the number of standard deviations to use for the Bollinger Bands calculation
bb_stddev = 2

# Replace with the symbol you want to trade (e.g. 'DOT/USDT')
symbol = 'DOT/USDT'

# Initialize the Bollinger Bands
# data = binance.fetch_ohlcv(symbol, timeframe='1m')
# closes = np.array([candle[4] for candle in data])
# upper, middle, lower = talib.BBANDS(closes, timeperiod=bb_period, nbdevup=bb_stddev, nbdevdn=bb_stddev, matype=0)

# Buy function
def buy():
    current_position_size = get_current_position_usdt()
    if current_position_size < investment_amount:
        investment_amount = polkaToBuy()
        order = binance.create_market_buy_order(symbol=symbol, amount=investment_amount) # Amount here it wants the number of polka

        #Print and return
        print('Buy Order: ', order['info']['orderId'])
        return order['info']['orderId']
    return None

# Sell function
def sell():
    current_position_size = get_current_position_size_polka()
    if current_position_size > 0:
        order = binance.create_market_sell_order(symbol=symbol, amount=get_current_position_size_polka())

        #Print and return
        print('Sell Order: ',order['info']['orderId'])
        return order['info']['orderId']
    return None

#Get current math of Polka after ((usdt * 0.5) / polkaPrice)
def polkaToBuy():
    return (get_current_position_usdt()*percentageAtUse)/binance.fetch_ticker(symbol)['bid']

# Calculate the current position size based on the current account balance
def get_current_position_usdt():
    balance = binance.fetch_balance()
    return balance['USDT']['free']  #/ binance.fetch_ticker(symbol)['bid']

# Calculate the current position size based on the current account balance
def get_current_position_size_polka():
    balance = binance.fetch_balance()
    return balance['DOT']['free'] / binance.fetch_ticker(symbol)['bid']

print('Polka Available Pre any Trades',get_current_position_size_polka())
print('USDT avilable pre any trades: ',get_current_position_usdt())

print('Price of Polka/usdt: ', binance.fetch_ticker(symbol)['bid'])
print('Quantity of polka to buy',polkaToBuy())

# print('buy info: ', buy())
# print('buy info: ', sell())

print('Polka Available Post any Trades',get_current_position_size_polka())
print('USDT avilable Post any trades: ',get_current_position_usdt())


# binance.create_market_buy_order(symbol=symbol, amount=50)
# print('bought')

# print(get_current_position_size())
# print(get_current_position_size()*0.5)

# print(binance.fetch_balance()['USDT']['free'])