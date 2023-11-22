from binance.client import Client
from binance.enums import *
import time
import math

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'
client = Client(api_key, api_secret)

symbol = 'SOLUSDT'
borrow_limit = 2

            # Currency type (SOLUSDT), (0.05) 5% Decimal percentage value of total margin
def open_long_position(symbol, borrow_limit):

    # Refresh margin account information
    account = client.get_margin_account(recvWindow=5000)

    # Get the current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])
    print(f"Current price of {symbol}: {price}")

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

    usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    print(f"Current margin account balance in USDT: {usdt_balance}")

    # Calculate the borrow amount based on the available balance and the borrow limit
    borrow_amount = round( ((usdt_balance * borrow_limit / price / step_size) * step_size),2 )

    # Borrow the required amount of margin
    client.create_margin_order(
        symbol=symbol,
        side=SIDE_BUY,
        type=ORDER_TYPE_MARKET,
        quantity=borrow_amount,
        sideEffectType='MARGIN_BUY',
        isIsolated='FALSE'
    )
    print(f"Opened Long position for {borrow_amount} {symbol} using 3x margin")

def close_long_position(symbol):
   
    #refresh account
    account = client.get_margin_account(recvWindow=5000)

    # Filter the list of open positions to get the position for SOL
    sol_position = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '')), None)
    quantity = float(sol_position['free'])

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

    # Round down the quantity to the nearest step size
    quantity = math.floor(quantity / step_size) * step_size     #make sure it's floored so we don't get invalid balance
    quantity = round(quantity,2)                                #make sure it only has 2 decimal spots

    # Close the long position and repay the borrowed USDT
    client.create_margin_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_MARKET,
        quantity=quantity,
        sideEffectType='AUTO_REPAY',
        isIsolated='FALSE'
    )
    print(f"Closed Long position for {quantity} {symbol} and repaid the 3x margin loan")


# get account
account = client.get_margin_account(recvWindow=5000)

#get long info
sol_position = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '')), None)
numberOfSol = float(sol_position['free'])

print('sol pos', numberOfSol)

if numberOfSol > 5:
    print('Long position detected')

    
else:    
    print('no position detected, running as usual')


print('Test Opening position')
open_long_position(symbol, borrow_limit)

time.sleep(5)

print('Test closing position')
close_long_position(symbol)

