import pandas as pd
import numpy as np
import requests
import time


# CoinGecko API endpoint for fetching historical candlestick data
endpoint = "https://api.coingecko.com/api/v3/coins/solana/market_chart"

# Parameters
vs_currency = "usd"  # The currency to compare against (in this case, USD)
days = 365          # Number of days of historical data

# Request parameters
params = {
    "vs_currency": vs_currency,
    "days": days
}

# Make API request
response = requests.get(endpoint, params=params)
data = response.json()

# Extracting candlestick data from the response
candlestick_data = data.get('prices', [])

timestamps = [entry[0] for entry in candlestick_data]
close_prices = [entry[1] for entry in candlestick_data]

# Creating a DataFrame from the extracted data
df = pd.DataFrame({
    'timestamp': pd.to_datetime(timestamps, unit='ms'),
    'close': close_prices
})

# Calculate MACD, Signal Line, and MACD Histogram
df['fast_ema'] = df['close'].ewm(span=12, min_periods=12).mean()
df['slow_ema'] = df['close'].ewm(span=26, min_periods=26).mean()
df['macd'] = df['fast_ema'] - df['slow_ema']
df['signal_line'] = df['macd'].ewm(span=9, min_periods=9).mean()
df['macd_histogram'] = df['macd'] - df['signal_line']

# Print the DataFrame with calculated indicators
print(df)

# Set parameters
stop_loss_percent = 0.015  # 1.5%
long_positions = []
short_positions = []

# ...

# ...

# Backtest the strategy
for i in range(1, len(df)):
    if df['macd'][i] > df['signal_line'][i] and df['macd'][i - 1] <= df['signal_line'][i - 1]:
        # Long entry
        entry_price = df['close'][i]
        stop_loss = entry_price * (1 - stop_loss_percent)
        entry_date = df['timestamp'][i]
        long_positions.append({'entry': entry_price, 'stop_loss': stop_loss, 'open_time': entry_date})
        
        print("Long Position:")
        print("Entry Date:", entry_date)
        print("Entry Price:", entry_price)
        print("Stop Loss:", stop_loss)
        
        # Find stop loss date for long position
        stop_loss_date = df[df['close'] <= stop_loss]['timestamp'].iloc[-1]
        
        # Calculate and store ideal take profit for long position
        df_subset = df[(df['timestamp'] >= entry_date) & (df['timestamp'] <= stop_loss_date)]
        if not df_subset.empty:
            peak_price = max(df_subset['close'])
            ideal_take_profit = ((peak_price - entry_price) / entry_price) * 100  # Convert to percentage
            long_positions[-1]['ideal_take_profit'] = ideal_take_profit  # Store in the last added position
            print("Ideal Take Profit:", f"{ideal_take_profit:.2f}%")
        else:
            long_positions[-1]['ideal_take_profit'] = None  # Store None when not calculated
            print("Ideal Take Profit:", "-")
        
        print()
        
    elif df['macd'][i] < df['signal_line'][i] and df['macd'][i - 1] >= df['signal_line'][i - 1]:
        # Short entry
        entry_price = df['close'][i]
        stop_loss = entry_price * (1 + stop_loss_percent)
        entry_date = df['timestamp'][i]
        short_positions.append({'entry': entry_price, 'stop_loss': stop_loss, 'open_time': entry_date})

        print("Short Position:")
        print("Entry Date:", entry_date)
        print("Entry Price:", entry_price)
        print("Stop Loss:", stop_loss)

        # Find stop loss date for short position
        stop_loss_date = df[df['close'] >= stop_loss]['timestamp'].iloc[-1]
        
        # Calculate and store ideal take profit for short position
        df_subset = df[(df['timestamp'] >= entry_date) & (df['timestamp'] <= stop_loss_date)]
        if not df_subset.empty:
            trough_price = min(df_subset['close'])
            ideal_take_profit = ((entry_price - trough_price) / entry_price) * 100  # Convert to percentage
            short_positions[-1]['ideal_take_profit'] = ideal_take_profit  # Store in the last added position
            print("Ideal Take Profit:", f"{ideal_take_profit:.2f}%")
        else:
            short_positions[-1]['ideal_take_profit'] = None  # Store None when not calculated
            print("Ideal Take Profit:", "-")
        
        print()

        
# ...


# Calculate averages for long positions
sum_long_take_profit = 0
count_long_positions = 0

for position in long_positions:
    ideal_take_profit = position.get('ideal_take_profit')
    if ideal_take_profit is not None:
        sum_long_take_profit += ideal_take_profit
        count_long_positions += 1

average_long_take_profit = sum_long_take_profit / count_long_positions if count_long_positions > 0 else 0

# Calculate averages for short positions
sum_short_take_profit = 0
count_short_positions = 0

for position in short_positions:
    ideal_take_profit = position.get('ideal_take_profit')
    print(ideal_take_profit)
    if ideal_take_profit is not None:
        sum_short_take_profit += ideal_take_profit
        count_short_positions += 1

average_short_take_profit = sum_short_take_profit / count_short_positions if count_short_positions > 0 else 0

print("Average Ideal Take Profit for Long Positions:", f"{average_long_take_profit:.2f}%")
print("Average Ideal Take Profit for Short Positions:", f"{average_short_take_profit:.2f}%")


print("New - Average Ideal Take Profit for Long Positions:", f"{0.6*average_long_take_profit:.2f}%")
print("New - Average Ideal Take Profit for Short Positions:", f"{0.6*average_short_take_profit:.2f}%")