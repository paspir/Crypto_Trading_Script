from binance.client import Client
from binance.enums import *
import time
import math
import datetime

"""                     --------- Notes: v8----------
* Add 5% stop loss to positions
*
"""

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'
client = Client(api_key, api_secret)

symbol = 'SOLUSDT'
borrow_limit = 0.07

def close_all_orders(symbol):
    # Get open orders for the symbol
    open_orders = client.get_open_margin_orders(symbol=symbol)
    
    # Cancel each open order
    for order in open_orders:
        order_id = order['orderId']
        client.cancel_margin_order(symbol=symbol, orderId=order_id)
        print(f"Cancelled order {order_id} for {symbol}")
    
    print("All existing orders have been closed.")

# Currency type (SOLUSDT), (0.05) 5% Decimal percentage value of total margin
def open_long_position(symbol, borrow_limit):

    # Refresh margin account information
    account = client.get_margin_account(recvWindow=5000)

    # Get the current price of the symbol
    ticker = client.get_symbol_ticker(symbol=symbol)
    price = float(ticker['price'])

 # Calculate the stop-loss price and limit price
    stop_loss_price = price * 0.95  # 5% stop-loss
    stop_loss_price = round((stop_loss_price), 2)

    limit_price = stop_loss_price * 0.99  # Set the limit price slightly below the stop price
    limit_price = round(limit_price, 2)

    # Get the step size for the symbol
    exchange_info = client.get_exchange_info()
    symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
    step_size = float(symbol_info['filters'][1]['stepSize'])

    usdt_balance = float([asset for asset in account['userAssets'] if asset['asset'] == 'USDT'][0]['free'])
    print(f"Current margin account balance in USDT: {usdt_balance}")

    # Calculate the borrow amount based on the available balance and the borrow limit
    borrow_amount = round( ((usdt_balance * borrow_limit / price / step_size) * step_size),2 )

    # # Borrow the required amount of margin
    # client.create_margin_order(
    #     symbol=symbol,
    #     side=SIDE_BUY,
    #     type=ORDER_TYPE_MARKET,
    #     quantity=borrow_amount,
    #     sideEffectType='MARGIN_BUY',
    #     isIsolated='FALSE'
    # )
    # message = (f"Open Long | {borrow_amount} {symbol} | at {symbol}: {price}")
    # print(message)


    borrow_amount = round((borrow_amount*0.99),2)

    print(borrow_amount, ' borrow_amount')
    print(stop_loss_price, ' stop_loss_price')
    print(limit_price, ' limit_price')

    order = client.create_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_STOP_LOSS_LIMIT,
        stopPrice=stop_loss_price,
        price=limit_price,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=borrow_amount
    )


def close_long_position(symbol):
   
    #refresh account
    account = client.get_margin_account(recvWindow=5000)

    close_all_orders(symbol)

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

#------------- Section that waits 4 hours & checks price nonstop - ----------------
                    # Get the current time
current_time = datetime.datetime.now()

# Calculate the start time of the next 4-hour candle
next_candle_time = current_time + datetime.timedelta(hours=4 - (current_time.hour % 4))
next_candle_time = next_candle_time.replace(minute=0, second=0, microsecond=0)

# Wait until the start time of the next 4-hour candle
while datetime.datetime.now() < next_candle_time:
    # Get the current price of SOL
    ticker = client.get_symbol_ticker(symbol=symbol)
    current_price = float(ticker['price'])
    print(current_price)

    # Sleep for 1 minute
    time.sleep(5)


# print('Test Opening position')
# open_long_position(symbol, borrow_limit)

# time.sleep(30)

# print('Test closing position')
# close_long_position(symbol)

