from backtest.BackExchange import BackExchange
from collections import deque


class TradingAlgo(object):
    def __init__(self, exchange: BackExchange):
        self.exchange = exchange
        self.last_price = 0

    def display_balance(self):
        pass

    def initialize(self):
        self.last_price = 0

    def execute(self):
        pass


class SimpleTradingAlgo(TradingAlgo):
    def __init__(self, exchange: BackExchange):
        super(SimpleTradingAlgo, self).__init__(exchange)

    def display_balance(self):
        balance = self.exchange.fetch_balance()
        for asset in balance:
            if balance[asset]['total'] > 0:
                print("{:<4} Total:{:>12}  In order:{:>12}  Remaining:{:>12}".format(
                    asset, round(balance[asset]['total'], 8), round(balance[asset]['used'], 8),
                    round(balance[asset]['free'], 8)))

    def execute(self):
        current_price = self.exchange.fetch_ticker('XRP/ETH')['open']
        balance = self.exchange.fetch_balance()
        if current_price < self.last_price:
            self.exchange.create_stop_limit_buy_order(symbol='XRP/ETH', amount=1000, price=1.3 * current_price,
                                                      stop_price=0.9 * current_price)
        elif balance['XRP']['free'] >= 1000.0:
            self.exchange.create_stop_limit_sell_order(symbol='XRP/ETH', amount=1000, price=0.3 * current_price,
                                                       stop_price=0.95 * current_price)
        self.last_price = current_price
        self.display_balance()
        print("Balance in ETH: {}".format(self.exchange.fetch_balance_in('ETH')))


class MovingAverageTradingAlgo(TradingAlgo):
    def __init__(self, exchange: BackExchange, window_size):
        super(MovingAverageTradingAlgo, self).__init__(exchange)
        self.moving_average = 0
        self.window_size = window_size
        self.price_queue = None

    def display_balance(self):
        balance = self.exchange.fetch_balance()
        for asset in balance:
            if balance[asset]['total'] > 0:
                print("{:<4} Total:{:>12}  In order:{:>12}  Remaining:{:>12}".format(
                    asset, round(balance[asset]['total'], 8), round(balance[asset]['used'], 8),
                    round(balance[asset]['free'], 8)))

    def initialize(self):
        self.moving_average = 0
        self.price_queue = deque(maxlen=self.window_size)

    def __get_moving_average(self, new_price):
        self.price_queue.append(new_price)
        if len(self.price_queue) < self.window_size:
            return None
        elif len(self.price_queue) == self.window_size:
            self.moving_average = sum(self.price_queue) / self.window_size
        else:
            self.moving_average += (new_price - self.price_queue.popleft()) / self.window_size
        return self.moving_average

    def execute(self):
        print(self.exchange.fetch_ticker('XRP/ETH'))
        current_price = self.exchange.fetch_ticker('XRP/ETH')['open']

        balance = self.exchange.fetch_balance()
        moving_average = self.__get_moving_average(current_price)
        if moving_average is None:
            print("ramp up period for moving average, do nothing")
            return
        else:
            print("moving average is:{:>12}".format(round(moving_average, 8)))
        if current_price < moving_average:
            self.exchange.create_limit_buy_order(symbol='XRP/ETH', amount=10, price=current_price)
        elif balance['XRP']['free'] >= 10.0:
            self.exchange.create_limit_sell_order(symbol='XRP/ETH', amount=10, price=current_price)
        self.last_price = current_price
        self.display_balance()
