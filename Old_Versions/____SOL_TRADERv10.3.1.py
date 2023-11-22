import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import talib
import math
from decimal import Decimal
import datetime
import math

"""                     ---------Notes: 10.3.1----------
* Fixed the logic for round numbers in: {Open&Close | Short&Long}
* Prints time when opening & Closing
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
borrow_limit = 2  # use 50% of available usd balance (add '*3' to use margin)

# Define variables to keep track of trade statistics
trades_won = 0
trades_lost = 0

#returns pnl
def getPnl(old,new):
    pnl = (new / old-1) *100
    return pnl

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
def get_Balance():
    #Refresh Margin account each loop incase of changes
    account1 = client.get_margin_account(recvWindow=5000)
    current_balance = float([asset for asset in account1['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    return current_balance

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
    
    # Wait for the next 15-minute candle before starting
    wait_for_next_15_minute_candle()


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
        step_size = float(symbol_info['filters'][1]['stepSize'])

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
        print(f"Closed short position for {quantity} {symbol} of the 3x margin account")

        #Wait for the next candle before starting
        wait_for_next_15_minute_candle()

#Run main loop
def run_loop():
    trades_won = 0
    trades_lost = 0

    #booleans for if else later
    long = False
    short = False

    #Get account info and do P&L
    account = client.get_margin_account(recvWindow=5000)

    #P&L Balance 1
    current_balance = get_Balance()
    #P&L Balance 2
    current_usdt_balance = get_Balance()
    #Calc P&L       bal2        /   bal1
    pnl = getPnl(current_balance, current_usdt_balance)
    

    #Wait for the next candle before starting
    wait_for_next_15_minute_candle()

    openPosition = None
    closePosition = None

    while True:
        try:

            #Refresh Margin account each loop incase of changes
            account = client.get_margin_account(recvWindow=5000)

            # -----------Get the last 100 15-minute candles for the symbol------------
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


            # Print Account info and trade status
            if long or short:
                trade_type = "Long" if long else "Short"
                print(f'[Runtime: {(time.time() - start_time)/60:.2f} Minutes] Won Trades: {trades_won} | Lost Trades: {trades_lost} | Session P&L: {pnl:.2f}% | USD Balance: {current_usdt_balance} | Trade Status: Open {trade_type} Position')
            else:
                print(f'[Runtime: {(time.time() - start_time)/60:.2f} Minutes] Won Trades: {trades_won} | Lost Trades: {trades_lost} | Session P&L: {pnl:.2f}% | USD Balance: {current_usdt_balance} | Trade Status: No Open Positions')
            
            # Print the current MACD values and moving averages
            print(f"MACD: {macd[-1]:.2f} | Signal: {signal[-1]:.2f} | Histogram: {hist[-1]:.2f}")
    
            #Long cross------------------------------------------------------
            if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
                # Open a long position

                if short:
                    # Check if a short position was previously opened but not closed, do this before
                    print(f'[{df.index[-1]}] Bullish signal: Closing Short Position')
                    close_short_margin_position(symbol)

                    # Do quick math for Win/L counter
                    closePosition = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
                    pnl2 = openPosition - closePosition

                    # Print the trade statistics and current P&L
                    print('Trade: ',pnl2, '$ | P&L')
                    if pnl2 > 0:
                        trades_won += 1
                    elif pnl2 < 0:
                        trades_lost += 1

                    #update p&L for print
                    pnl = getPnl(current_balance, current_usdt_balance)

                    short = False

                    #Refresh Balance: 
                    current_usdt_balance = get_Balance()

                elif not long:
                    
                    print(f'[{df.index[-1]}] Bullish signal: Opening Long Position')

                        #Store this for later pnl2 math
                    openPosition = current_usdt_balance 
                        #Open the trade
                    open_long_position(symbol, borrow_limit)
                        #Set trade long to true so the code knows theres a long trade open
                    long = True

            #Cross Down
            elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
               
                if long:
                    # Check if a long position was previously opened but not closed
                    print(f'[{df.index[-1]}] Bearish signal: Closing Long Position')
                    close_long_position(symbol)

                    # Do quick math for Win/L counter
                    closePosition = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
                    pnl2 = openPosition - closePosition

                    # Print the trade statistics and current P&L
                    pnl2 = openPosition - closePosition
                    print(pnl2, '$ | P&L')
                    if pnl2 > 0:
                        trades_won += 1
                    elif pnl2 < 0:
                        trades_lost += 1
                    
                    #update p&L for print
                    pnl = getPnl(current_balance, current_usdt_balance)

                    long = False

                    #Refresh Balance: 
                    current_usdt_balance = get_Balance()

                # Open a short position
                elif not short:
                    
                    print(f'[{df.index[-1]}] Bearish signal: Opening Short Position')

                        #Store this for later pnl2 math
                    openPosition = current_usdt_balance 
                        #Open the trade
                    open_short_margin_position(symbol, borrow_limit)
                        #Set trade short to true so the code knows theres a short trade open
                    short = True


            # time.sleep(60 * 15)  # wait for 15 minutes before the next iteration
           
            # Sleeps until next 15 min candle
            current_time = datetime.datetime.now()
            next_interval = (current_time + datetime.timedelta(minutes=15)).replace(second=0, microsecond=0)
            time.sleep((next_interval - current_time).total_seconds())
                        
        
        except Exception as e:
                

                # Print the error message
            print(f'Error: {str(e)}')

            # Wait for 1 minute before trying again
            time.sleep(60)
            
            # Try to close the long position if it is open
            if long:
                print(f'[{df.index[-1]}] Exception: Long position being closed')
                # Close the Position
                while True:
                    try:
                        close_long_position(symbol)
                        long = False
                        break
                    except Exception as e:
                        print(f'Error closing long position: {str(e)}')
                        time.sleep(60)
                        
            # Try to close the short position if it is open
            if short:
                print(f'[{df.index[-1]}] Exception: Short position being closed')
                # Close the Position
                while True:
                    try:
                        close_short_margin_position(symbol)
                        short = False
                        break
                    except Exception as e:
                        print(f'Error closing short position: {str(e)}')
                        time.sleep(60)
                        
            # Restart the exception handling block if an error occurs during the exception handling block
            continue

if __name__ == '__main__':
    start_time = time.time()
    run_loop()