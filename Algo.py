from backtest.BackExchange import BackExchange


class TradingAlgo(object):
    def __init__(self, exchange: BackExchange):
        self.exchange = exchange

    def display_balance(self):
        balance = self.exchange.fetch_balance()
        for asset in balance:
            if balance[asset]['total'] > 0:
                print("{:<4} Total:{:>12}  In order:{:>12}  Remaining:{:>12}".format(
                    asset, round(balance[asset]['total'], 8), round(balance[asset]['in order'], 8),
                    round(balance[asset]['available'], 8)))

    def initialize(self):
        self.last_price = 0

    def execute(self):
        print(self.exchange.fetch_ticker('XRP/ETH'))
        current_price = self.exchange.fetch_ticker('XRP/ETH')['open']
        balance = self.exchange.fetch_balance()
        if current_price < self.last_price:
            id = self.exchange.create_limit_buy_order(symbol='XRP/ETH', amount=10, price=current_price)
        elif balance['XRP']['available'] >= 10.0:
            id = self.exchange.create_limit_sell_order(symbol='XRP/ETH', amount=10, price=current_price)
        self.last_price = current_price
        self.display_balance()
