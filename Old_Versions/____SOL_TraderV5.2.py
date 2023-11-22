import time
import talib
import ccxt
import requests
import json
import numpy as np

# Define the API keys and parameters
binance = ccxt.binance({
    'apiKey': '',
    'secret': '',
    'enableRateLimit': True,
})

# Define the Pushover keys and parameters
pushover_api_token = ''
pushover_user_key = ''
pushover_url = 'https://api.pushover.net/1/messages.json'

# Define the trading parameters
symbol = 'SOL/USDT'
fast_period = 12
slow_period = 26
signal_period = 9
margin_type = 'isolated'
leverage = 3
position_size = 0.6

# Define the trade variables
prev_macd = None
prev_signal = None
position = None
trade_count = 0
win_count = 0
loss_count = 0
total_pnl = 0

# Define the function to place a long or short order
def place_order(side, price):
    # Calculate the position size
    balance = binance.fetch_balance()['USDT']['free']
    max_size = (balance * leverage * position_size) / price
    order_size = min(max_size, balance * leverage)

    if side == 'buy':
        # Place a buy order
        order = binance.create_market_buy_order(symbol, order_size, {'type': margin_type, 'leverage': leverage})
        return order
    elif side == 'sell':
        # Place a short sell order
        # Step 1: Place a limit sell order at the desired price
        limit_price = price * 0.98  # set limit price 2% below current price
        limit_order = binance.create_limit_sell_order(symbol, order_size, limit_price, {'type': margin_type, 'leverage': leverage})

        # Step 2: Borrow the required amount of the quote currency (USDT) for the position size
        borrow_amount = limit_order['cost'] * leverage
        binance.create_margin_loan(symbol.split('/')[1], borrow_amount)

        # Step 3: Place a margin sell order to sell the borrowed assets
        sell_order = binance.create_market_sell_order(symbol, order_size, {'type': margin_type, 'leverage': leverage})

        # Step 4: Repay the borrowed quote currency and place a limit buy order to close the position
        binance.repay_margin_loan(symbol.split('/')[1], borrow_amount)
        limit_price = price * 1.02  # set limit price 2% above current price
        limit_order = binance.create_limit_buy_order(symbol, order_size, limit_price, {'type': margin_type, 'leverage': leverage})
        
        return limit_order


# Define the function to send a Pushover notification
def send_notification(message):
    data = {
        'token': pushover_api_token,
        'user': pushover_user_key,
        'message': message
    }
    response = requests.post(pushover_url, data=data)
    return response


# Start the trading loop
while True:
    try:
        # Get the MACD indicator for the last 1000 candles
        candles = binance.fetch_ohlcv(symbol, timeframe='15m', limit=1000) #Candle Length
        close_prices = np.array([candle[4] for candle in candles])
        macd, signal, _ = talib.MACD(close_prices, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
        macd = macd[-1]
        signal = signal[-1]

        # Check if we have a position open
        if position is not None:
            # Check if we need to close the position
            if (prev_macd is not None and prev_signal is not None and 
                ((position == 'long' and macd < signal) or (position == 'short' and macd > signal))):
                if position == 'long':
                    pnl = position['amount'] * (binance.fetch_ticker(symbol)['last'] - position['price'])
                    total_pnl += pnl
                    win_count += 1 if pnl > 0 else 0
                    loss_count += 1 if pnl < 0 else 0
                elif position == 'short':
                    pnl = position['amount'] * (position['price'] - binance.fetch_ticker(symbol)['last'])
                    total_pnl += pnl
                    win_count += 1 if pnl > 0 else 0
                    loss_count += 1 if pnl < 0 else 0
                    message = f"Closed short position with P&L of {pnl} USDT. New balance is {binance.fetch_balance()['USDT']['free']} USDT."
                send_notification(message)
                position = None
                prev_macd = None
                prev_signal = None

        # Check if we need to open a new position
        if prev_macd is not None and prev_signal is not None and ((prev_macd < prev_signal and macd > signal) or (prev_macd > prev_signal and macd < signal)):
            if macd > signal:
                # Place a long order
                order = place_order('buy', binance.fetch_ticker(symbol)['last'])
                position = {
                    'side': 'long',
                    'amount': order['filled'],
                    'price': order['average'],
                }
                message = f"Opened long position at {position['price']} USDT. New balance is {binance.fetch_balance()['USDT']['free']} USDT."
            else:
                # Place a short order
                order = place_order('sell', binance.fetch_ticker(symbol)['last'])
                position = {
                    'side': 'short',
                    'amount': order['filled'],
                    'price': order['average'],
                }
                message = f"Opened short position at {position['price']} USDT. New balance is {binance.fetch_balance()['USDT']['free']} USDT."
            send_notification(message)
        
        # Update the previous MACD and signal values
        prev_macd = macd
        prev_signal = signal

        # Print the current trade statistics
        trade_count += 1
        win_rate = win_count / trade_count
        print(f"Trade #{trade_count}: MACD = {macd:.2f}, Signal = {signal:.2f}, Position = {position}, Win Rate = {win_rate:.2f}, Total P&L = {total_pnl:.2f} USDT")

        # Wait for 10 mins before the next iteration
        time.sleep(60 * 10)

    except Exception as e:
        # Print any errors that occur and wait for 5 minutes before the next iteration
        print(f"An error occurred: {e}")
        time.sleep(150)

