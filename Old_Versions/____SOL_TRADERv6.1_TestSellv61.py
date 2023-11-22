from binance.client import Client
from binance.enums import *
import time
import math

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'
client = Client(api_key, api_secret)

# Set up the trading parameters
symbol = 'SOLUSDT'
borrow_limit = 0.3  # borrow up to 5% of the available balance for testing purposes

# Define the functions for opening and closing margin positions

def open_short_margin_position(symbol, borrow_limit):

    # Refresh margin account information
    account = client.get_margin_account(recvWindow=5000)

    # Get the current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price']) 

    # #5% stop loss (2.5% at 2x leverage)
    # stop_loss = price * stopShortPrice
    # take_profit = price * profitShortPrice

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

    usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    print(f"Current margin account balance in USDT: {usdt_balance}")

    # Calculate the borrow amount based on the available balance and the borrow limit - Round to second decimal spot
    borrow_amount = round(((usdt_balance * borrow_limit / price / step_size) * step_size),2)

    # Borrow the required amount of margin
    client.create_margin_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_MARKET,
        quantity=borrow_amount,
        sideEffectType='MARGIN_BUY',
        isIsolated='FALSE'
    )
    message = (f"* Open Short | {borrow_amount} {symbol} | at {symbol}: {price} ")
    print(message)
    

def close_short_margin_position(symbol):
    # Refresh margin account information
    account = client.get_margin_account()

    # Filter the list of borrowed assets to get the borrowed amount of SOL
    borrowed_sols = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '') and p['borrowed'] != '0'), None)
    if borrowed_sols is not None:
        print(f"Current borrowed amount of {symbol} in margin account: {float(borrowed_sols['borrowed'])}")
        # Close the short position and repay the borrowed USDT
        quantity = float(borrowed_sols['borrowed'])

        # Get the step size for the symbol
        exchange_info = client.get_exchange_info()
        symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
        step_size = float(symbol_info['filters'][1]['stepSize'])

            # Get the current price of the symbol - to print after
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])

        quantity = math.floor(quantity / step_size) * step_size  # round to the nearest step size - Floor
        quantity = round((quantity),2)  #make sure its 2 decimal spots
        
        client.create_margin_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            sideEffectType='AUTO_REPAY',
            isIsolated='FALSE'
        )
        message = (f"* Closed Short | {quantity} {symbol} | at {symbol}: {price}")
        print(message)


# account = client.get_margin_account(recvWindow=5000)
# # Filter the list of borrowed assets to get the borrowed amount of SOL
# borrowed_sols = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '') and p['borrowed'] != '0'), None)
# borrowed_quantity = float(borrowed_sols['borrowed'])
# print('short amount: ', borrowed_quantity)

# #get long info
# sol_position = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '')), None)
# numberOfSol = float(sol_position['free'])

# print('long amount', numberOfSol)

# Wait for some time before closing the position
time.sleep(3)

print('open short')

# Open a short margin position
open_short_margin_position(symbol, borrow_limit)

# Wait for some time before closing the position
time.sleep(5)

# print('close short')

# # Close the short margin position
close_short_margin_position(symbol)


