import time
from binance.client import Client
from binance.enums import *
import talib

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'
client = Client(api_key, api_secret)

# Set up the trading parameters
symbol = 'SOLUSDT'
quantity = 57 # the amount of the cryptocurrency you want to trade
borrow_limit = 3 # the maximum margin borrowing limit
trade_type = ORDER_TYPE_MARKET # use a market order

# Place a long order using 3x margin
borrow_amount = round(quantity * borrow_limit - quantity, 2)
client.create_margin_order(symbol=symbol, side=SIDE_BUY, type=trade_type, quantity=quantity, isIsolated='FALSE')
client.create_margin_loan(asset=symbol.replace('USDT', ''), amount=borrow_amount)
print(f'Bought {quantity} {symbol} at market price using 3x margin')

# Wait for 10 seconds
time.sleep(10)

# Close the long order and repay the margin loan
client.create_margin_order(symbol=symbol, side=SIDE_SELL, type=trade_type, quantity=quantity, isIsolated='FALSE')
repay_amount = round(quantity * borrow_limit, 2)
client.repay_margin_loan(asset=symbol.replace('USDT', ''), amount=repay_amount)
print(f'Sold {quantity} {symbol} at market price and repaid {repay_amount} {symbol} of the margin loan')
