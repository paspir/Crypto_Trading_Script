import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import talib
import math
import datetime
import math
import requests

"""                     --------- Notes: 11.1 ----------
* adding pushover keys to text my phone when trades open & close with price of sol
* Fixed wait 4 hour candle to be printing properly
* Texts phone an update at each candle
"""

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'

# Define the Pushover keys and parameters
pushover_api_token = 'pushover api token goes here'
pushover_user_key = 'pushover user key'
pushover_url = 'https://api.pushover.net/1/messages.json'

# Initialize the Binance client
client = Client(api_key=API_KEY, api_secret=API_SECRET)

# Define the trading parameters
symbol = 'SOLUSDT'
fast_period = 5
slow_period = 15
signal_period = 9
borrow_limit = 2  # use 50% of available usd balance (add '*3' to use margin)

# Define the function to send a Pushover notification
def send_notification(message):
    data = {
        'token': pushover_api_token,
        'user': pushover_user_key,
        'message': message
    }
    response = requests.post(pushover_url, data=data)
    return response

#Wait until next 4 hour
def wait_for_next_4_hour_candle():
    now = datetime.datetime.now()
    current_time = now.time()
    current_hour = current_time.hour
    hours_to_wait = 4 - (current_hour % 4)
    minutes_to_wait = (hours_to_wait * 60) - current_time.minute
    seconds_to_wait = minutes_to_wait * 60
    wait_time = datetime.timedelta(seconds=seconds_to_wait)
    
    hours_remaining = int(wait_time.total_seconds() // 3600)
    minutes_remaining = int((wait_time.total_seconds() % 3600) // 60)
    
    print(f"Waiting for {hours_remaining} hours and {minutes_remaining} minutes until the next 4-hour candle starts.")
    
    time.sleep(seconds_to_wait)
    
    print("4-hour candle is starting now!")


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
    message = (f"Open Long | {borrow_amount} {symbol} | at {symbol}: {price}")
    print(message)

    #Text phone
    send_notification(message)

def close_long_position(symbol):
   
    #refresh account
    account = client.get_margin_account(recvWindow=5000)

    # Filter the list of open positions to get the position for SOL
    sol_position = next((p for p in account['userAssets'] if p['asset'] == symbol.replace('USDT', '')), None)
    quantity = float(sol_position['free'])

    # Get the current price of the symbol - to print after
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

    # Round down the quantity to the nearest step size
    quantity = math.floor(quantity / step_size) * step_size   
    quantity = round(quantity,2)                                

    # Close the long position and repay the borrowed USDT
    client.create_margin_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_MARKET,
        quantity=quantity,
        sideEffectType='AUTO_REPAY',
        isIsolated='FALSE'
    )
    message = (f"Closed Long | {quantity} {symbol} | at {symbol}: {price}")
    print(message)

     #Text phone
    send_notification(message)
    
    # Wait for the next 15-minute candle before starting
    wait_for_next_4_hour_candle()

def open_short_margin_position(symbol, borrow_limit):

    # Refresh margin account information
    account = client.get_margin_account(recvWindow=5000)

    # Get the current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price']) 

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
    message = (f"Opened Short | {borrow_amount} {symbol} | at {symbol}: {price}")
    print(message)

     #Text phone
    send_notification(message)

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
        message = (f"Closed Short | {quantity} {symbol} | at {symbol}: {price}")
        print(message)

         #Text phone
        send_notification(message)

        #Wait for the next candle before starting
        wait_for_next_4_hour_candle()

def run_loop():
    #booleans for if else later
    long = False
    short = False

    message = None
    #Balance
    current_usdt_balance = get_Balance()

    #Wait for the next candle before starting
    wait_for_next_4_hour_candle()

    while True:
        try:

            # -----------Get the last 100 4-hour candles for the symbol------------
            klines = client.get_klines(symbol=symbol, interval=KLINE_INTERVAL_4HOUR, limit=100)

            # Convert the klines data to a Pandas dataframe
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                            'quote_asset_volume', 'num_trades', 'taker_buy_base_asset_volume',
                                            'taker_buy_quote_asset_volume', 'ignore'])

            # Convert the timestamp to a datetime object and set it as the index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')

            # Resample the dataframe to 4-hour candlesticks
            df = df.resample('4H').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum',
                                        'close_time': 'last', 'quote_asset_volume': 'sum', 'num_trades': 'sum',
                                        'taker_buy_base_asset_volume': 'sum', 'taker_buy_quote_asset_volume': 'sum',
                                        'ignore': 'last'})

            # Calculate the MACD indicator
            macd, signal, hist = talib.MACD(df['close'], fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)

            # Print Account info and trade status
            if long or short:
                trade_type = "Long" if long else "Short"
                print(f'[Runtime: {(time.time() - start_time)/60:.2f} | USD Balance: {current_usdt_balance} | Trade Status: Open {trade_type} Position')
                message = (f'USD Balance: {current_usdt_balance} | Trade Status: Open {trade_type} Position')
                send_notification(message)
            else:
                print(f'[Runtime: {(time.time() - start_time)/60:.2f} | USD Balance: {current_usdt_balance} | Trade Status: No Open Positions')
                message = (f'USD Balance: {current_usdt_balance} | Trade Status: No Open Positions')
                send_notification(message)

            
            # Print the current MACD values and moving averages
            print(f"MACD: {macd[-1]:.2f} | Signal: {signal[-1]:.2f} | Histogram: {hist[-1]:.2f}")
    
            #Long cross------------------------------------------------------
            if macd[-1] > signal[-1] and macd[-2] < signal[-2]:
                # Open a long position

                if short:
                    # Check if a short position was previously opened but not closed, do this before
                    print(f'[{df.index[-1]}] Bullish signal: Closing Short Position')
                    close_short_margin_position(symbol)

                    short = False
                    current_usdt_balance = get_Balance()

                elif not long:
                    print(f'[{df.index[-1]}] Bullish signal: Opening Long Position')

                    #Open the trade
                    open_long_position(symbol, borrow_limit)

                    #set to long
                    long = True

            #Cross Down
            elif macd[-1] < signal[-1] and macd[-2] > signal[-2]:
               
                if long:
                    # Check if a long position was previously opened but not closed
                    print(f'[{df.index[-1]}] Bearish signal: Closing Long Position')
                    close_long_position(symbol)
                    
                    long = False
                    current_usdt_balance = get_Balance()

                # Open a short position
                elif not short:
                    print(f'[{df.index[-1]}] Bearish signal: Opening Short Position')

                    #Open the trade
                    open_short_margin_position(symbol, borrow_limit)

                    #set short to true
                    short = True

            # Sleeps until next 4-hour candle
            current_time = datetime.datetime.now()
            next_interval = current_time + datetime.timedelta(hours=4)
            next_interval = next_interval.replace(minute=0, second=0, microsecond=0)
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