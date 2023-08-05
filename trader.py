import requests
from binance.um_futures import UMFutures
import os
import shutil

TEST_ENDPOINT = "https://testnet.binancefuture.com"

with open("api_key.txt", "r") as secret:
    i = secret.read().split("\n")
    API_KEY = i[0]
    API_SECRET = i[1]

'''
Binance API Info:
- All endpoints return either a JSON object or array.
- Data is reurned in ASCENDING order: oldest first, newest last.
- All time/timestamp fields are in milliseconds.
'''

client = UMFutures(key=API_KEY, secret=API_SECRET, base_url=TEST_ENDPOINT)

try:
    client.balance()
except:
    print("could not connect to binance, check api key/secret")
    exit()

def get_hourly_sma(symbol, num_hours):
    '''
    [
        1607444700000,          // Open time
        "18879.99",             // Open
        "18900.00",             // High
        "18878.98",             // Low
        "18896.13",             // Close (or latest price)
        "492.363",              // Volume
        1607444759999,          // Close time
        "9302145.66080",        // Quote asset volume
        1874,                   // Number of trades
        "385.983",              // Taker buy volume
        "7292402.33267",        // Taker buy quote asset volume
        "0"                     // Ignore.
    ]
    '''
    kline_data = client.continuous_klines(pair=symbol, 
        contractType="PERPETUAL", interval="1h", limit=num_hours)
    return sum([float(i[4]) for i in kline_data])/len(kline_data)
    # 4th item

def get_daily_sma(symbol, num_days):
    kline_data = client.continuous_klines(pair=symbol, 
        contractType="PERPETUAL", interval="1d", limit=num_days)
    return sum([float(i[4]) for i in kline_data])/len(kline_data)


SYMBOLS = ["BTCUSDT", "BCHUSDT", "ETHUSDT", "ETCUSDT", "LTCUSDT", "XRPUSDT", 
    "EOSUSDT"]

# for all coins, get daily sma and hourly sma.
symbols_data = {}

for i in SYMBOLS:
    j = get_hourly_sma(i, 24)
    k = get_daily_sma(i, 30)
    symbols_data[i] = {
        "short_term_sma": j, 
        "long_term_sma": k, 
        "diff": j-k, "percentage": (j-k)/k,
        "current": float(client.ticker_price(i)["price"])
    }
    
# find the minimum and maximum percentages and we will have a bucket
# with both of them for buying and selling

min_sym = min(symbols_data, key = lambda k: symbols_data[k]["percentage"])
max_sym = max(symbols_data, key = lambda k: symbols_data[k]["percentage"])

# if min or max are not negative or positive respectively don't do it
if symbols_data[min_sym]["percentage"] > 0 or symbols_data[max_sym]["percentage"] < 0:
    #exit()
    pass

print(symbols_data)
CAP = 100.0

order_data = [
    {
        "symbol": max_sym,
        "side": "BUY",
        "positionSide": "LONG",
        "quantity": str(round(CAP/symbols_data[max_sym]["current"], 2)),
        "type": "MARKET",
        "reduceOnly": "false",
        #"price": symbols_data[max_sym]["current"]
    },
    {
        "symbol": min_sym,
        "side": "SELL",
        "positionSide": "SHORT",
        "quantity": str(round(CAP/symbols_data[min_sym]["current"], 2)),
        "type": "MARKET"
        #"price": symbols_data[min_sym]["current"]
    }
]
print(order_data)

# else we can commit to the trade.
#i = client.new_batch_order(order_data)

def get_account_positions():
    return [i for i in client.account()["positions"] if float(i["positionAmt"]) != 0]

def close_all_positions():
    positions = get_account_positions()
    # note we can only have up to 5 positions in the batch order.
    while len(positions) > 0:
        order_list = []
        for i in range(5):
            if len(positions) <= 0: break
            j = positions[-1]
            order_list.append({
                "symbol": j["symbol"],
                "side": ("SELL" if j["positionSide"] == "LONG" else "BUY"),
                "positionSide": j["positionSide"],
                "quantity": (j["positionAmt"] if j["positionAmt"][0] != "-" \
                    else j["positionAmt"][1:]),
                "type": "MARKET",
            })
            positions.pop()
        #print(order_list, "\n")
        print(client.new_batch_order(order_list))

close_all_positions()