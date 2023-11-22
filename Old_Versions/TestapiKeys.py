import requests
import time
import hmac
from urllib.parse import urlencode
import hashlib

# Define your Binance API credentials
API_KEY = 'binance api key here'
API_SECRET = 'binance api secret here'

# Define API endpoint and parameters
endpoint = 'https://api.binance.com/api/v3/account'
params = {'timestamp': int(time.time() * 1000)}

# Add API key to headers
headers = {'X-MBX-APIKEY': api_key}

# Sign request with API secret
signature = hmac.new(api_secret.encode('utf-8'), urlencode(params).encode('utf-8'), hashlib.sha256).hexdigest()
params['signature'] = signature

# Send API request
response = requests.get(endpoint, headers=headers, params=params)
# Check response status code
if response.status_code == 200:
    print('API keys are valid')
else:
    print('API keys are invalid')
    print(response.json())
