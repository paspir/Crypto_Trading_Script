import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import talib
import math

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'

# Initialize the Binance client
client = Client(api_key=API_KEY, api_secret=API_SECRET)

# Define the trading parameters
symbol = 'SOLUSDT'
fast_period = 5
slow_period = 15
signal_period = 9
borrow_limit = 0.05  # use 5% of available margin balance

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
    # Initialize the trade statistics
    # global trades_won, trades_lost
    trades_won = 0
    trades_lost = 0
    # USe this to track open position or not
    position_open = False

    while True:
        # Get the last 100 15-minute candles for the symbol
        klines = client.get_klines(symbol=symbol, interval=KLINE_INTERVAL_15MINUTE, limit=100)

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

        # Check the current P&L
        current_usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
        pnl = (current_usdt_balance / current_balance - 1) * 100

        # # Check if the MACD line crossed above the signal line to open a long position
        # if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
        #     # Open a long position
        #     open_long_position(symbol, borrow_limit)
        #     print(f'[{df.index[-1]}] Opened long position')

        # # Check if the MACD line crossed below the signal line to open a short position
        # elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
        #     # Open a short position
        #     open_short_margin_position(symbol, borrow_limit)
        #     print(f'[{df.index[-1]}] Opened short position')

        # # Check if the MACD line crossed above the signal line to close the short position
        # elif macd[-1] > signal[-1] and macd[-2] < signal[-2]:
        #     # Close the short position
        #     close_short_margin_position(symbol)
        #     print(f'[{df.index[-1]}] Closed short position')
        #     if pnl > 0:
        #         trades_won += 1
        #     elif pnl < 0:
        #         trades_lost += 1

        # # Check if the MACD line crossed below the signal line to close the long position
        # elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
        # # Close the long position
        #     close_long_position(symbol)
        #     print(f'[{df.index[-1]}] Closed long position')
        #     # Print the trade statistics and current P&L
        #     if pnl > 0:
        #         trades_won += 1
        #     elif pnl < 0:
        #         trades_lost += 1


        if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
            # Open a long position
            if not position_open:
                open_long_position(symbol, borrow_limit)
                print(f'[{df.index[-1]}] Opened long position')
                position_open = True

        elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
            # Open a short position
            if not position_open:
                open_short_margin_position(symbol, borrow_limit)
                print(f'[{df.index[-1]}] Opened short position')
                position_open = True

        elif macd[-1] > signal[-1] and macd[-2] < signal[-2] and position_open:
            # Close the short position
            close_short_margin_position(symbol)
            print(f'[{df.index[-1]}] Closed short position')
            position_open = False
            # Print the trade statistics and current P&L
            if pnl > 0:
                trades_won += 1
            elif pnl < 0:
                trades_lost += 1

        elif macd[-1] < signal[-1] and macd[-2] > signal[-2] and position_open:
            # Close the long position
            close_long_position(symbol)
            print(f'[{df.index[-1]}] Closed long position')
            position_open = False
            # Print the trade statistics and current P&L
            if pnl > 0:
                trades_won += 1
            elif pnl < 0:
                trades_lost += 1




        usdCount = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
        # print(f'[Runtime: {time.time() - start_time:.2f}s] Won Trades: {trades_won} | Lost Trades: {trades_lost} | '
        #     f'Current P&L: {pnl:.2f}%')
        
        
        print(f'[Runtime: {time.time() - start_time:.2f}s] Won Trades: {trades_won} | Lost Trades: {trades_lost} | Current P&L: {pnl:.2f}% | USD Balance: {usdCount}')


        # Print the current MACD values and moving averages
        print(f"MACD: {macd[-1]:.2f} | Signal: {signal[-1]:.2f} | Histogram: {hist[-1]:.2f}")

        time.sleep(600)  # wait for 10 minutes before the next iteration


if __name__ == '__main__':
    start_time = time.time()
    trades_won = 0
    trades_lost = 0
    run_loop()