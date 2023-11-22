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
fast_period = 5
slow_period = 15
signal_period = 9
quantity = 10 # the amount of the cryptocurrency you want to trade
borrow_limit = 3 # the maximum margin borrowing limit
trade_type = ORDER_TYPE_MARKET # use a market order

# Initialize the variables for tracking trades and performance
last_macd = None
trades_placed = 0
won_trades = 0
lost_trades = 0
total_gain = 0.0
total_loss = 0.0

# Main trading loop
while True:
    try:
        # Get the current price and historical data
        klines = client.get_klines(symbol=symbol, interval=KLINE_INTERVAL_15MINUTE)
        prices = np.array([float(kline[4]) for kline in klines])

        # Calculate the MACD indicator
        macd, signal, hist = talib.MACD(prices, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)

        # Check if the MACD line crosses the signal line
        if macd[-1] > signal[-1] and last_macd and last_macd < signal[-1]:
            # Place a buy order using 3x margin
            borrow_amount = round(quantity * borrow_limit - quantity, 2)
            client.create_margin_order(symbol=symbol, side=SIDE_BUY, type=trade_type, quantity=quantity, isIsolated='FALSE')
            client.create_margin_loan(asset=symbol.replace('USDT', ''), amount=borrow_amount)
            print(f'Bought {quantity} {symbol} at {prices[-1]} using 3x margin')

            # Update the trading variables
            trades_placed += 1
            won_trades += 1
            total_gain += prices[-1] * quantity * borrow_limit

        elif macd[-1] < signal[-1] and last_macd and last_macd > signal[-1]:
            # Close the non-margin portion of the position to free up balance for margin loan repayment
            non_margin_quantity = quantity * (borrow_limit + 1)
            client.create_order(symbol=symbol, side=SIDE_SELL, type=trade_type, quantity=non_margin_quantity)
            print(f'Sold {non_margin_quantity} {symbol} at {prices[-1]} to free up balance for margin loan repayment')

            # Place a sell order to close the margin portion of the position and repay the margin loan
            margin_quantity = quantity
            client.create_margin_order(symbol=symbol, side=SIDE_SELL, type=trade_type, quantity=margin_quantity, isIsolated='FALSE')
            repay_amount = round(margin_quantity * borrow_limit, 2)
            client.repay_margin_loan(asset=symbol.replace('USDT', ''), amount=repay_amount)
            print(f'Sold {margin_quantity} {symbol} at {prices[-1]} and repaid {repay_amount} {symbol} of the margin loan')

            # Update the trading variables
            trades_placed += 1
            lost_trades += 1
            total_loss += prices[-1] * quantity * borrow_limit

        # Print the trading performance
        print(f'Trades placed: {trades_placed}, Won: {won_trades}, Lost: {lost_trades}')
        print(f'Total gain: {total_gain}, Total loss: {total_loss}, Net gain: {total_gain - total_loss}')

        # Update the last MACD value
        last_macd = macd[-1]

        # Sleep for a minute
        time.sleep(60)

    except Exception as e:
        print(f'Error: {e}')
        time.sleep(10)

