import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import talib
import math
import datetime

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'

# Initialize the Binance client
client = Client(api_key=API_KEY, api_secret=API_SECRET)

def wait_for_next_15_minute_candle():
    now = datetime.datetime.now()
    current_time = now.time()
    current_minute = current_time.minute
    minutes_to_wait = 15 - (current_minute % 15)
    wait_time = datetime.timedelta(minutes=minutes_to_wait)
    
    print(f"Waiting for {wait_time.total_seconds() // 60} minutes until the next 15 minute candle starts.")
    
    while wait_time.total_seconds() > 0:
        print(f"{wait_time.total_seconds() // 60} minutes remaining...")
        time.sleep(60)
        wait_time -= datetime.timedelta(minutes=1)
        
    print("15 minute candle is starting now!")

# Define the trading parameters
symbol = 'SOLUSDT'
fast_period = 5
slow_period = 15
signal_period = 9
borrow_limit = 0.03  # use 30% of available margin balance

# Define variables to keep track of trade statistics
trades_won = 0
trades_lost = 0

account = client.get_margin_account(recvWindow=5000)
current_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])

# Define the functions for opening and closing margin positions
def open_long_position(symbol, borrow_limit):
    # Refresh margin account information
    account = client.get_margin_account(recvWindow=5000)
    usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])

    # Get the current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])
    print(f"Current price of {symbol}: {price}")

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

    # Get the current margin account balance in USDT
    account = client.get_margin_account()
    usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    print(f"Current margin account balance in USDT: {usdt_balance}")

    # Calculate the borrow amount based on the available balance and the borrow limit
    borrow_amount = round(usdt_balance * borrow_limit / price / step_size) * step_size

    # Borrow the required amount of margin
    client.create_margin_order(
        symbol=symbol,
        side=SIDE_BUY,
        type=ORDER_TYPE_MARKET,
        quantity=borrow_amount,
        sideEffectType='MARGIN_BUY',
        isIsolated='FALSE'
    )
    print(f"Opened Long position for {borrow_amount} USDT worth of {symbol} using 3x margin")

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
    quantity = math.floor(quantity / step_size) * step_size

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

    # Get the current margin account balance in USDT
    account = client.get_margin_account()
    usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    print(f"Current margin account balance in USDT: {usdt_balance}")

    # Calculate the borrow amount based on the available balance and the borrow limit
    borrow_amount = round(usdt_balance * borrow_limit / price / step_size) * step_size

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
        step_size = next((f['stepSize'] for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        if step_size is None:
            raise Exception('Failed to get step size from exchange info')

        quantity = round(quantity / float(step_size)) * float(step_size)  # round to the nearest step size

        client.create_margin_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            sideEffectType='AUTO_REPAY',
            isIsolated='FALSE'
        )
        print(f"Closed short position for {quantity} {symbol} of the 3x margin account")

# Define the loop function
def run_loop():

    #Wait untiol next 15 min candle to start same time
    wait_for_next_15_minute_candle()

    while True:
        # Get the last 100 15-minute candles for the symbol
        klines = client.get_klines(symbol=symbol, interval=KLINE_INTERVAL_15MINUTE, limit=100)

        #Make them global to fix error
        global trades_won, trades_lost

        # Convert the klines data to a Pandas dataframe
        df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                           'quote_asset_volume', 'num_trades', 'taker_buy_base_asset_volume',
                                           'taker_buy_quote_asset_volume', 'ignore'])

        # Convert the timestamp to a datetime object and set it as the index
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')

        # Calculate the MACD indicator
        macd, signal, hist = talib.MACD(df['close'], fastperiod=fast_period, slowperiod=slow_period,
                                         signalperiod=signal_period)

        # Check if the MACD line crossed above the signal line to open a long position
        if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
            # Open a long position
            open_long_position(symbol, borrow_limit)
            print(f'[{df.index[-1]}] Opened long position')

        # Check if the MACD line crossed below the signal line to open a short position
        elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
            # Open a short position
            open_short_margin_position(symbol, borrow_limit)
            print(f'[{df.index[-1]}] Opened short position')

        # Check if the MACD line crossed above the signal line to close the short position
        elif macd[-1] > signal[-1] and macd[-2] < signal[-2]:
            # Close the short position
            close_short_margin_position(symbol)
            print(f'[{df.index[-1]}] Closed short position')

        # Check if the MACD line crossed below the signal line to close the long position
        elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
        # Close the long position
            close_long_position(symbol)
            print(f'[{df.index[-1]}] Closed long position')

        # Check the current P&L
        current_usdt_balance = float(client.get_asset_balance(asset='USDT')['free'])
        pnl = (current_usdt_balance / current_balance - 1) * 100

        # Print the trade statistics and current P&L
        if pnl > 0:
            trades_won += 1
        elif pnl < 0:
            trades_lost += 1
        print(f'[Runtime: {time.time() - start_time:.2f}s] Won Trades: {trades_won} | Lost Trades: {trades_lost} | '
            f'Current P&L: {pnl:.2f}%')

        time.sleep(450)  # wait for 7.5 minutes before the next iteration

if __name__ == '__main__':
    start_time = time.time()
    run_loop()