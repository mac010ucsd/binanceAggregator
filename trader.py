import requests
from binance.um_futures import UMFutures
import os
import shutil
import random

class trader:

    def __init__(self, key, secret, 
        endpoint="https://testnet.binancefuture.com"):
        
        if endpoint == "https://testnet.binancefuture.com":
            print("The endpoint is the Binance Testnet endpoint.")
        elif endpoint == "https://fapi.binance.com":
            print("The endpoint is the Binance Live endpoint. \
                Proceed with caution.")
        else:
            raise ValueError("The endpoint is undefined. \
                Please use the Binance testnet or live endpoint.")
        
        self.client = UMFutures(key=key, secret=secret, base_url=endpoint)

        # try to connect to client. will throw some kind of error if invalid
        # api key, secret, or endpoint.
        self.client.balance()
        print("Successfully connected to the endpoint.")

        self.symbol_data = {}
        
        self.get_exchange_info()

    def get_symbol_data(self):
        return self.symbol_data

    def get_exchange_info(self, perpetualOnly=True):
        # get exchange info, reformat it so that it's easy for us to work with.
        
        ex_info = self.client.exchange_info()

        for sym in ex_info["symbols"]:

            # check if perpetual. we only want perpetual contracts
            if sym["contractType"] != "PERPETUAL":
                continue

            self.symbol_data[sym["symbol"]] = sym
            self.symbol_data[sym["symbol"]]["filters"] = \
                {i["filterType"]: i for i in sym["filters"]}
            
    def qty_min(self, sym):
        # get min purchase qty
        return float(self.symbol_data[sym]["filters"]["LOT_SIZE"]["minQty"])
    
    def price_min(self, sym):
        # min token price
        return float(self.symbol_data[sym]["filters"]["PRICE_FILTER"]["minPrice"])
    
    def get_precision(self, sym, mode="P"):
        # get lowest qty precision, in decimals
        if type(mode) is not str:
            raise TypeError("mode should be a string, either Q for Quantity \
                            or P for Price.")
        mode = mode.lower()
        
        if mode == "p":
            i = self.symbol_data[sym]["filters"]["PRICE_FILTER"]["tickSize"]
        elif mode == "q":            
            i = self.symbol_data[sym]["filters"]["LOT_SIZE"]["stepSize"]
        else:
            raise ValueError("mode should either be P or Q for \
                             Quantity or Price")
        
        if i.find(".") != -1:
            return i[::-1].strip("0").find(".")
        else:
            return -1*len(i)+1

    
    def get_markprice(self, sym):
        return float(self.client.mark_price(sym)["markPrice"])

    def max_market_symbol(self):
        # want to get the most expensive minimum purchase for a symbol.
        # this will be useful to determine how large our orders must be.
        # max token name not needed right now, just have it just because.
        max_token_val = 0
        max_token_name = None

        mark_prices = self.client.mark_price()

        for i in mark_prices:

            cur_token_name = i["symbol"]

            if cur_token_name not in self.symbol_data:
                # sometimes the token exists in one but not the other. 
                # let's just ignore that.
                continue

            cur_token_val = (float(i["markPrice"])
                * float(self.qty_min(cur_token_name)))
            
            if cur_token_val > max_token_val:
                max_token_val = cur_token_val
                max_token_name = cur_token_name

        return max_token_name, max_token_val

    def get_hourly_sma(self, symbol, num_hours):

        kline_data = self.client.continuous_klines(pair=symbol, 
            contractType="PERPETUAL", interval="1h", limit=num_hours)
        return sum([float(i[4]) for i in kline_data])/len(kline_data)

    def get_hourly_wma(self, symbol, num_hours):

        kline_data = self.client.continuous_klines(pair=symbol, 
            contractType="PERPETUAL", interval="1h", limit=num_hours)
        return sum(
            [float(kline_data[i][4])*(num_hours-i) for i in range(num_hours)]
            )*2/(num_hours*(num_hours+1))

    def get_daily_sma(self, symbol, num_days, kline_data=None):

        if kline_data is None:
            kline_data = self.client.continuous_klines(pair=symbol, 
                contractType="PERPETUAL", interval="1d", limit=num_days)
            
        return sum([float(i[4]) for i in kline_data])/len(kline_data)

    def get_daily_wma(self, symbol, num_days):

        kline_data = self.client.continuous_klines(pair=symbol, 
            contractType="PERPETUAL", interval="1d", limit=num_days)
        return sum(
            [float(kline_data[i][4])*(num_days-i) for i in range(num_days)]
            )*2/(num_days*(num_days+1))

    def get_daily_ema(self, symbol, num_days):
        kline_data = self.client.continuous_klines(pair=symbol, 
            contractType="PERPETUAL", interval="1d", limit=num_days)
        
        # randomly decided that I will take 2x num of days
        # then take 1/4 for SMA
        # then next 3/4 for EMA.
        # there's no logic behind this.

        weighting = 2/(num_days+1)
        cur_ema = self.get_daily_sma(symbol, num_days//4, 
                                kline_data[num_days-num_days//4:])
        for i in range(num_days-num_days//4, 0, -1):
            cur_ema = (float(kline_data[i][4])-cur_ema)*weighting+cur_ema
        return cur_ema
    
    def get_all_symbols(self):
        return self.symbol_data.keys()

    def get_account_positions(self):
        return [i for i in self.client.account()["positions"] if 
            float(i["positionAmt"]) != 0]
    
    def purchase_random(self, num):
        # Purchase a random selection of symbols. Spend the minimum amount
        # possible on each symbol.
        if num > len(self.get_symbol_data()):
            raise ValueError(f"Number of symbols to purchase must be \
                less than or equal to {len(self.get_symbol_data())}")
        
        order_book = []

        # note: min purchase value should be greater than $5 USDT if made
        # through the api. requirement, code "-4164"
        for i in random.sample(list(self.get_all_symbols()), num):
            
            short = random.randint(0,1)
            mp = round(self.get_markprice(i), self.get_precision(i, mode="p"))
            qty = 5/mp

            if self.qty_min(i)*mp > 5:
                qty = self.qty_min(i)*mp

            qty = round(qty, self.get_precision(i, mode="q"))
            while (qty * mp < 5):
                qty = round(qty + 
                    float(self.symbol_data[i]["filters"]["LOT_SIZE"]["stepSize"]), 
                    self.get_precision(i, mode="q"))

            order_book.append({
                "symbol": i,
                "side": "SELL" if short else "BUY",
                "positionSide": "SHORT" if short else "LONG",
                "quantity": str(round(qty, 
                    self.get_precision(i, mode="q"))),
                "price": str(round(mp, self.get_precision(i, mode="p"))),
                "type": "LIMIT",
                "timeInForce": "GTC"
            })

        print(order_book)
        for i in range(0, num, 5):
            print(self.client.new_batch_order(
                order_book[i:(i+5 if i+5 < num else num)]))
        
        #print(order_list, "\n")

#SYMBOLS = ["BTCUSDT", "BCHUSDT", "ETHUSDT", "ETCUSDT", "LTCUSDT", "XRPUSDT", 
#    "EOSUSDT"]

'''
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

#print(symbols_data)
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
#print(order_data)

# else we can commit to the trade.
#i = client.new_batch_order(order_data)

#i = len(client.exchange_info()["symbols"])

#print(i)

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
'''

#close_all_positions()
'''
print(get_daily_ema("BTCUSDT", 100))

print(get_daily_sma("BTCUSDT", 9))

print(get_daily_wma("BTCUSDT", 9))
'''

    
with open("api_key.txt", "r") as secret:
    i = secret.read().split("\n")
    API_KEY = i[0]
    API_SECRET = i[1]

me = trader(API_KEY, API_SECRET)

print(me.max_market_symbol())

me.purchase_random(15)