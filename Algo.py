from backtest.BackExchange import BackExchange


class TradingAlgo(object):
    def __init__(self, exchange: BackExchange):
        self.exchange = exchange
        self.last_price = 0

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
        current_price = self.exchange.fetch_ticker('XRP/ETH')['open']
        balance = self.exchange.fetch_balance()
        if current_price < self.last_price:
            self.exchange.create_stop_limit_buy_order(symbol='XRP/ETH', amount=1000, price=1.3 * current_price,
                                                      stop_price=0.9 * current_price)
        elif balance['XRP']['available'] >= 1000.0:
            self.exchange.create_stop_limit_sell_order(symbol='XRP/ETH', amount=1000, price=0.3 * current_price,
                                                       stop_price=0.95 * current_price)
        self.last_price = current_price
        self.display_balance()
        # TODO: balance_in is NOT defined, fix it.
        # print("Balance in ETH: {}".format(self.exchange.balance_in('ETH')))
