# Test code to place a long order with borrowing
import ccxt

# Define the API keys and parameters
binance = ccxt.binance({
    'apiKey': '',
    'secret': '',
    'enableRateLimit': True,
})

# Set the trading parameters
symbol = 'SOL/USDT'
leverage = 3
position_size = 0.6


# Define the function to place a long order with borrowing
def place_order(price):
    # Check the USDT margin balance (not isolated)
    balance = binance.fetch_balance(params={'type': 'margin'})
    usdt_balance = balance['USDT']['total']

    # Calculate the position size
    max_size = (usdt_balance * leverage * position_size) / price
    order_size = min(max_size, usdt_balance * leverage)

    # Calculate the amount of USDT to borrow
    borrow_amount = order_size / leverage

    # Place a long buy order with borrowing
    order = binance.create_market_buy_order(
        symbol,
        order_size,
        {
            'type': 'margin',
            'leverage': leverage,
            'isIsolated': False,
            'params': {
                'borrowable': borrow_amount
            }
        }
    )

    return order



# Get the current market price for SOL/USDT
price = binance.fetch_ticker(symbol)['last']

# Place a long order with borrowing for 10 SOL
order = place_order(price)

# Print the order information
print('Order placed:')
print('  Symbol:', order['symbol'])
print('  Side:', order['side'])
print('  Type:', order['type'])
print('  Status:', order['status'])
print('  Executed amount:', order['filled'])
print('  Average price:', order['average'])
print('  Cost:', order['cost'])