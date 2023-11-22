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
borrow_limit = 0.03  # borrow up to 5% of the available balance for testing purposes

# Define the functions for opening and closing margin positions

#Ceil
def open_short_margin_position(symbol, borrow_limit):

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

    # Adjust the quantity to the nearest step size precision - Floor
    borrow_amount = math.ceil(borrow_amount / step_size) * step_size

    # Borrow the required amount of margin
    client.create_margin_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_MARKET,
        quantity=borrow_amount,
        sideEffectType='MARGIN_BUY',
        isIsolated='FALSE'
    )
    print(f"Opened Short position for {borrow_amount} {symbol} using 3x margin")
    

def close_short_margin_position(symbol):
    # Refresh margin account information
    account = client.get_margin_account(recvWindow=5000)

    # Filter the list of borrowed assets to get the borrowed amount of SOL
    borrowed_sols = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '') and p['borrowed'] != '0'), None)
    if borrowed_sols is not None:
        print(f"Current borrowed amount of {symbol} in margin account: {float(borrowed_sols['borrowed'])}")

        # Close the short position and repay the borrowed USDT
        quantity = float(borrowed_sols['borrowed'])

        # Get the step size for the symbol
        symbol_info = next((s for s in client.get_exchange_info()['symbols'] if s['symbol'] == symbol), None)
        step_size = float(symbol_info['filters'][1]['stepSize'])

        # Adjust the quantity to the nearest step size precision - Floor
        quantity = math.floor(quantity / step_size) * step_size

        client.create_margin_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            sideEffectType='AUTO_REPAY',
            isIsolated='FALSE'
        )
        print(f"Closed short position for {quantity} {symbol} of the 3x margin account")

# Wait for some time before closing the position
time.sleep(3)

print('open short')

# Open a short margin position
open_short_margin_position(symbol, borrow_limit)

# Wait for some time before closing the position
time.sleep(10)

print('close short')

# Close the short margin position
close_short_margin_position(symbol)


