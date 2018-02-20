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
        self.price_queue = deque(maxlen=window_size+1)
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
        self.price_queue = deque(maxlen=window_size+1)
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


"""
MACD is an indicator of indicators (EMA)
"""
class MACD(OperatorsBase):
    def __init__(self, exchange: BackExchange, ticker_name: str, field: QuoteFields):
        super(SMA, self).__init__(exchange)
        self.ticker_name = ticker_name
        self.ema_26 = EMA(exchange, ticker_name, 26, field)
        self.ema_12 = EMA(exchange, ticker_name, 12, field)
        self.macd = None
        self.operator_name = "SMA" + " of " + ticker_name

    def get(self):
        if self.last_timestamp == self.exchange.current_timestamp:
            print("You attempt to calculate {} twice at ts={}".format(self.operator_name, self.last_timestamp))
            print("Please save it to a local variable and reuse it elsewhere, now using calculated value.")
            return self.macd
        ema_12 = self.ema_12.get()
        ema_26 = self.ema_26.get()
        if ema_12 is None or ema_26 is None:
            return None
        else:
            self.macd = ema_12 - ema_26
            return self.macd


"""
Stochastic Oscillator
it returns both %K and %D, while oscillator is commonly
used to check if %K crossed %D
"""
class StochasticOscillator(OperatorsBase):
    def __init__(self, exchange: BackExchange, ticker_name: str):
        super(SMA, self).__init__(exchange)
        self.ticker_name = ticker_name
        self.low_14 = None
        self.high_14 = None
        self.price_queue = deque(maxlen=14)
        self.stochastic_oscillator = None
        self.past_oscillator = deque(maxlen=3)
        self.operator_name = "StochasticOscillator" + " of " + ticker_name

    def get(self):
        if self.last_timestamp == self.exchange.current_timestamp:
            print("You attempt to calculate {} twice at ts={}".format(self.operator_name, self.last_timestamp))
            print("Please save it to a local variable and reuse it elsewhere, now using calculated value.")
            return self.stochastic_oscillator

        current_close = self.exchange.fetch_ticker(self.ticker_name)[QuoteFields.Close]
        if len(price_queue) < 14:
            self.price_queue.append(current_close)
            return None
        self.low_14 = min(price_queue)
        self.high_14 = max(price_queue)
        self.price_queue.append(current_close)
        self.stochastic_oscillator = round((current_close - self.low_14) / (self.high_14 - self.low_14) * 100, 2)
        self.past_oscillator.append(self.stochastic_oscillator)
        if len(self.past_oscillator) < 3:
            return self.stochastic_oscillator, None
        return self.stochastic_oscillator, round(sum(self.past_oscillator) / 3, 2)