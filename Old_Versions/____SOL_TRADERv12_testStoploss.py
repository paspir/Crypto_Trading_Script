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

"""                     --------- Notes: v12.0 ----------
* Add 5% stop loss to positions - BY CHECKING eahc minute price of sol
*  at end of loop checks if long or short -> if either of these checks every minute the price of sol for stop loss trigger
* if a stop loss condition is triggered closes position adn texts my phone -> depending onwait 4 hr end of closing positions
* then breaking the loop and continuing normal code
* 
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

def run_loop():
    #booleans for if else later
    long = False
    short = True

    ticker = client.get_symbol_ticker(symbol=symbol)
    current_price = float(ticker['price'])

    stop_loss = current_price * 0.98


    while True:

            print('Before if else')

            if long or short:
    # ------------------ Section that waits 4 hours & checks price nonstop - ----------------
                    # Get the current time
                current_time = datetime.datetime.now()

                if long:
                     print('long')
                elif short:
                     print('short')
                # Calculate the start time of the next 4-hour candle
                next_candle_time = current_time + datetime.timedelta(hours=4 - (current_time.hour % 4))
                next_candle_time = next_candle_time.replace(minute=0, second=0, microsecond=0)

                # Wait until the start time of the next 4-hour candle
                while datetime.datetime.now() < next_candle_time:
                    # Get the current price of SOL
                    ticker = client.get_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])

                    print( 'Position Open: Checking for stop loss cross')

                    # Logic for Trading  and stop losses
                    if long and (current_price < stop_loss):

                        message = (f'[Stop Loss {stop_loss} Triggered: Closing Long Position')
                        print(message)

                        break   # Break into regular code, leaving it to wait for next 4 hour to do the work

                    elif short and (current_price > stop_loss):

                        # Check if a short position was previously opened but not closed, do this before
                        message = (f' Stop Loss {stop_loss} Triggered: Closing Short Position')
                        print(message)

                        break # Break into regular code, leaving it to wait for next 4 hour to do the work

                    # Sleep for 15 seconds
                    time.sleep(4)

            # else no trades are open.. do regular code
            else:   
                print('no position open sleep 30 seconds')
                time.sleep(30)

            print('Loop exited')
            time.sleep(60)

        

if __name__ == '__main__':
    start_time = time.time()
    run_loop()