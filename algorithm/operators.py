##############
# Efficient operators like SMA, EMA etc
# those operators are all sub-classes of a base operator
# which defines basic storage structure to enable efficient calculation of those indicators
# 1, initialize.
#   to construct an operator, we need to initialize basic parameters that define this operator
# 2, internal storage
#   stock indicators usually rely on price history, therefore we allow customized storage of price history
#   for each operator.
# 3, online calculation
#   calculation of indicators should be efficient: i.e. it only needs input of price of the current
#   time stamp, while utilizing its internal storage for necessary modifications. If necessary, a
#   @memorized or @lazy_evaluate might be used.
#############

from backtest.BackExchange import BackExchange
from core.Quote import QuoteFields

from collections import deque


class OperatorsBase(object):
    def __init__(self, exchange: BackExchange):
        self.exchange = exchange
        self.last_timestamp = 0
        self.operator_name = ""
        pass

    def get(self):
        pass


class EMA(OperatorsBase):
    def __init__(self, exchange: BackExchange, ticker_name: str, window_size : int, field: QuoteFields):
        super(SMA, self).__init__(exchange)
        self.ticker_name = ticker_name
        self.window_size = window_size
        self.price_queue = deque(maxlen=window_size)
        self.field = field
        self.ema = None
        self.multiplier = 2 / (1 + window_size)
        self.operator_name = "EMA(" + str(window_size) + ")" + " of " + ticker_name

    def get(self):
        if self.last_timestamp == self.exchange.current_timestamp:
            print("You attempt to calculate {} twice at ts={}".format(self.operator_name, self.last_timestamp))
            print("Please save it to a local variable and reuse it elsewhere, now using calculated value.")
            return self.ema
        current_price = self.exchange.fetch_ticker(self.ticker_name)[self.field]
        self.price_queue.append(current_price)
        if len(self.price_queue) < self.window_size:
            return self.ema
        elif len(self.price_queue) == self.window_size:
            self.ema = sum(self.price_queue) / self.window_size
        else:
            self.ema += (current_price - self.price_queue.popleft()) * self.multiplier
        self.last_timestamp = self.exchange.current_timestamp
        return self.ema



class SMA(OperatorsBase):
    def __init__(self, exchange: BackExchange, ticker_name: str, window_size : int, field: QuoteFields):
        super(SMA, self).__init__(exchange)
        self.ticker_name = ticker_name
        self.window_size = window_size
        self.price_queue = deque(maxlen=window_size)
        self.field = field
        self.sma = None
        self.operator_name = "SMA(" + str(window_size) + ")" + " of " + ticker_name

    def get(self):
        if self.last_timestamp == self.exchange.current_timestamp:
            print("You attempt to calculate {} twice at ts={}".format(self.operator_name, self.last_timestamp))
            print("Please save it to a local variable and reuse it elsewhere, now using calculated value.")
            return self.sma
        current_price = self.exchange.fetch_ticker(self.ticker_name)[self.field]
        self.price_queue.append(current_price)
        if len(self.price_queue) < self.window_size:
            return self.sma
        elif len(self.price_queue) == self.window_size:
            self.sma = sum(self.price_queue) / self.window_size
        else:
            self.sma += (current_price - self.price_queue.popleft()) / self.window_size
        self.last_timestamp = self.exchange.current_timestamp
        return self.sma