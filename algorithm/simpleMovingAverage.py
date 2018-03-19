from backtest.BackExchange import BackExchange
from collections import deque


class MovingAverageTradingAlgo(object):
    def __init__(self, exchange: BackExchange):
        self.exchange = exchange
        self.moving_average = 0
        self.price_queue = None
        self.window_size = 0
        self.last_price = 0

    def display_balance(self):
        balance = self.exchange.fetch_balance()
        for asset in balance:
            if balance[asset]['total'] > 0:
                print("{:<4} Total:{:>12}  In order:{:>12}  Remaining:{:>12}".format(
                    asset, round(balance[asset]['total'], 8), round(balance[asset]['used'], 8),
                    round(balance[asset]['free'], 8)))

    def initialize(self, window_size):
        self.moving_average = 0
        self.price_queue = deque(maxlen=window_size)
        self.window_size = window_size

    def get_moving_average(self, new_price):
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
        moving_average = self.get_moving_average(current_price)
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
