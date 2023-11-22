import oandapyV20
import oandapyV20.endpoints.instruments as instruments
import pandas

# Define the account and API details
accountID = ''
access_token = ''
client = oandapyV20.API(access_token=access_token, environment='practice')

# Define the instrument and request parameters
instrument = 'EUR_USD'
params = {'count': 10, 'granularity': 'D'}




asset_info = client.get_symbol_info('SOLUSDT')
precision = asset_info['filters'][2]['stepSize']

# Request the candle data
r = instruments.InstrumentsCandles(instrument=instrument, params=params)
candles = client.request(r)['candles']



# Print the closing prices of the candles
for c in candles:
    print(c['mid']['c'])
