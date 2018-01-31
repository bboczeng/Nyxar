# use a dict/list to maintain the position for every tradable assets
# use two lists to store history order and open order
# suggest create a class for order
# open order structure:
# timestamp (when placing it) | pair | order type: makret/limit | a bool for buy/sell | number | filled percentage
# history order structure
# timestamp (when filled) | pair | a bool for buy/sell | number

# do you think it is necessary to give every asset an unique number ID?

# here is what happens when a new timestamp is being processed:
# exchange check if there are open orders remaining
#   - If there are, check if orders can be filled or not, then update the position
# exchange sends the latest quote to the trading algo
# exchange takes request (place order / cancel order / history order / current position) from the trading algo, 
# then process it

# not sure about the time ordering here. but i think one should place order at current tick and process it at the
# next tick? or order is always processed within the same price in the same tick


# How to check if orders can be filled? (For OHLCV data)
# Market order:
# 1. Set the price to be this tick's close price (should be flexible to tune this. for example, use high for buy or
#    low to sell)
# 2. Slippage model. Here we first implement a fixed basispoint model. 0.05% fee for all trading, i.e., additional 
#    0.05% for buy, less 0.05% for sell. 
# 3. Check if there are enough quote currency based on the price. If not, (i never use market order. don't know if 
#    we should reject the order, or fill as much as possible)
# 4. If the order is only paritially filled, update the filled percentage and leave it in the open order for next cycle


# more to come
# exchange should be able to accept (optional) bid/ask, along with OHLCV. the slippage model should be able to run based
# on it. i think slippage is particularly important in cryptocurrency, due to the lack of liquidity and large bid-ask 
# spread for altcoins

from enum import Enum
import math


class OrderType(Enum):
    Limit = "limit"
    Market = "market"


class Order(object):
    def __init__(self, name, price, size, type, timestamp):
        assert isinstance(type, OrderType), "type must be OrderType"
        assert size >= 0, "size must be a positive number"
        assert price >= 0, "price must be a positive number"
        self.timestamp = timestamp  # a string timestamp
        self.name = name  # asset name, TODO: can be force to be an ID
        self.size = size
        self.price = price
        self.type = type

    def price(self):
        return self.price

    def size(self):
        return self.size

    def type(self):
        return self.type

    def timestamp(self):
        return self.timestamp

    def name(self):
        return self.name


class OpenOrder(Order):
    def __init__(self, price, size, type, timestamp):
        super(OpenOrder, self).__init__(price, size, type, timestamp)
        # initially, open order's filling percentage is 0
        self.fill_percentage = 0

    def get_unfilled_amount(self):
        return self.fill_percentage * self.size

    def get_fillable_amount(self, try_amount):
        return try_amount if try_amount <= self.get_unfilled_amount() else self.get_unfilled_amount()

    def fill(self, amount):
        # Python 3 auto converts to float
        self.fill_percentage += (amount / self.size)

    def filled(self):
        # still we use 10^-9 as float error
        return math.abs(self.fill_percentage - 1.0) < 10**(-9)



class OrderBook(object):
    def __init__(self):
        self.buys = []
        self.sells = []

    # True: buy; False: sell
    def add_order(self, order, buy=True):
        if buy:
            self.add_buy_order(order)
        else:
            self.add_sell_order(order)

    def add_buy_order(self, order):
        pass

    def add_sell_order(self, order):
        pass


class OpenOrderBook(OrderBook):
    def __init__(self):
        super(OpenOrderBook, self).__init__()


class HistoryOrderBook(OrderBook):
    def __init__(self):
        super(HistoryOrderBook, self).__init__()


class Record(object):
    def __init__(self):
        self.cash = 0
        self.open_orders = OpenOrderBook()
        self.history_orders = HistoryOrderBook()


    def get_average_cost(self):
        pass

    def submit_limit_order(self):
        pass

    def submit_market_order(self):
        pass


    # always execute this line for each timestamp during backtest
    def resolve_open_orders(self):
        pass