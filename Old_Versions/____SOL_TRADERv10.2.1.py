import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import talib
import math
from decimal import Decimal
import datetime

"""                     ---------10.2.1----------
* Too many issues with 10.4, opening & closing trades, not seeing clues.
* 10.2 opened a short, but couldn't close it..
* Fixed logic in IF statements, to cover all possibilities of code.
* implemented wait_for_next_15_minute_candle, never had any problems
* New if else print implemeted but has ## been commented !!
                        --------------------------
"""

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

# Returns USD balance
def get_Balance(account):
    current_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    return current_balance

def get_Precision(symbol):
    info = client.get_symbol_info(symbol)
    symbol_info = next((x for x in info['filters'] if x['filterType'] == 'PRICE_FILTER'), None)
    precision = int(round(-math.log(float(symbol_info['tickSize']), 10), 0))
    return precision


# Define the functions for opening and closing margin positions
def open_long_position(symbol, borrow_limit, usdt_balance):

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


def open_short_margin_position(symbol, borrow_limit, usdt_balance):

    # Get the current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])
    print(f"Current price of {symbol}: {price}")

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

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


def run_loop():
    trades_won = 0
    trades_lost = 0

    #booleans for if else later
    long = False
    short = False

    account = client.get_margin_account(recvWindow=5000)
    current_balance = get_Balance(account)
    
    #Wait for the next candle before starting
    wait_for_next_15_minute_candle()

    openPosition = None
    closePosition = None

    while True:

        #Refresh Margin account each loop incase of changes
        account = client.get_margin_account(recvWindow=5000)
        
        # Check the current P&L
        current_usdt_balance = get_Balance(account)
        pnl = (current_usdt_balance / current_balance - 1) * 100

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
        

        #Long cross
        if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
            # Open a long position

            if short:
                # Check if a short position was previously opened but not closed, do this before
                print(f'[{df.index[-1]}] MacD upcross, short position being closed')
                close_short_margin_position(symbol)

                # Do quick math for Win/L counter
                usdCount1 = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
                closePosition = current_usdt_balance - usdCount1

                # Print the trade statistics and current P&L
                pnl2 = openPosition - closePosition
                print(pnl2, '$ | P&L')
                if pnl2 > 0:
                    trades_won += 1
                elif pnl2 < 0:
                    trades_lost += 1

                short = False

            elif not long:
                open_long_position(symbol, borrow_limit, current_usdt_balance)
                print(f'[{df.index[-1]}] Opened long position')

                # Do quick math for Win/L counter
                usdCount1 = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
                openPosition = current_usdt_balance - usdCount1

                long = True

        #Cross Down
        elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
           
            if long:
                # Check if a long position was previously opened but not closed
                print(f'[{df.index[-1]}] MacD downcross, Long position being closed')
                close_long_position(symbol)

                # Do quick math for Win/L counter
                usdCount1 = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
                closePosition = current_usdt_balance - usdCount1

                # Print the trade statistics and current P&L
                pnl2 = openPosition - closePosition
                print(pnl2, '$ | P&L')
                if pnl2 > 0:
                    trades_won += 1
                elif pnl2 < 0:
                    trades_lost += 1

                long = False

            # Open a short position
            elif not short:
                open_short_margin_position(symbol, borrow_limit, current_usdt_balance)
                print(f'[{df.index[-1]}] Opened short position')

                # Do quick math for Win/L counter
                usdCount1 = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
                openPosition = current_usdt_balance - usdCount1

                short = True
            

        usdCount = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
        
        #Print Account info
        print(f'[Runtime: {time.time() - start_time:.2f}s] Won Trades: {trades_won} | Lost Trades: {trades_lost} | Current P&L: {pnl:.2f}% | USD Balance: {usdCount}')

        # Print Account info and trade status
        if long or short:
            trade_type = "Long" if long else "Short"
            print(f'[Runtime: {time.time()/60 - start_time:.2f} Minutes] Won Trades: {trades_won} | Lost Trades: {trades_lost} | Current P&L: {pnl:.2f}% | USD Balance: {usdCount} | Trade Status: Open {trade_type} Position')
        else:
            print(f'[Runtime: {time.time()/60 - start_time:.2f} Minutes] Won Trades: {trades_won} | Lost Trades: {trades_lost} | Current P&L: {pnl:.2f}% | USD Balance: {usdCount} | Trade Status: No Open Positions')

        # Print the current MACD values and moving averages
        print(f"MACD: {macd[-1]:.2f} | Signal: {signal[-1]:.2f} | Histogram: {hist[-1]:.2f}")

        time.sleep(600)  # wait for 10 minutes before the next iteration


if __name__ == '__main__':
    start_time = time.time()
    run_loop()