import time
import numpy as np
from binance.client import Client
from binance.enums import *
import talib

# Set up the Binance API client with your API keys
# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'
client = Client(api_key, api_secret)

# Set up the trading parameters
symbol = 'SOLUSDT'
quantity = 10 # the amount of the cryptocurrency you want to trade
borrow_limit = 3 # the maximum margin borrowing limit
trade_type = ORDER_TYPE_MARKET # use a market order

# Open a long order using 3x margin
borrow_amount = round(quantity * borrow_limit - quantity, 2)
client.create_margin_order(symbol=symbol, side=SIDE_BUY, type=trade_type, quantity=quantity, isIsolated='FALSE')
client.create_margin_loan(asset=symbol.replace('USDT', ''), amount=borrow_amount)
print(f'Bought {quantity} {symbol} at market price using 3x margin')

#Wait for 10 seconds
time.sleep(10)



# Close all of our SOL position and repay the outstanding debt in USDT
balances = client.get_margin_account()['userAssets']
sol_balance = float(next(item for item in balances if item["asset"] == 'SOL' and item["borrowed"] != "0")['free'])
usdt_balance = float(next(item for item in balances if item["asset"] == 'USDT' and item["borrowed"] != "0")['free'])

# Calculate the maximum amount of SOL that can be sold to repay the margin loan
max_sell_quantity = round(sol_balance * 0.98, 2)

# Close the non-margin portion of the position to free up balance for margin loan repayment
non_margin_quantity = quantity * (borrow_limit + 1)
client.create_order(symbol=symbol, side=SIDE_SELL, type=trade_type, quantity=non_margin_quantity)
print(f'Sold {non_margin_quantity} {symbol} at market price to free up balance for margin loan repayment')

# Place a sell order to close the margin portion of the position and repay the margin loan
margin_quantity = min(max_sell_quantity, quantity)
usdt_debt = round(margin_quantity * borrow_limit, 2)
client.create_margin_order(symbol=symbol, side=SIDE_SELL, type=trade_type, quantity=margin_quantity, isIsolated='FALSE')
client.repay_margin_loan(asset='USDT', amount=usdt_debt)
print(f'Sold {margin_quantity} {symbol} at market price and repaid {usdt_debt} USDT of the margin loan')
