from backtest.BackExchange import BackExchange
from backtest.Order import OrderSide


class TradingAlgo(object):
    def __init__(self, exchange: BackExchange):
        self.exchange_api = exchange

    def display_balance(self):
        balance = self.exchange_api.get_balance()
        for asset in balance:
            if balance[asset]['total'] > 0:
                print("{:<4} Total:{:>12}  In order:{:>12}  Remaining:{:>12}".format(
                    asset, round(balance[asset]['total'], 8), round(balance[asset]['in_order'], 8),
                    round(balance[asset]['total'] - balance[asset]['in_order'], 8)))

    def execute(self):
        print("Timestamp: ", self.exchange_api.current_timestamp)
        data = self.exchange_api.get_price('XRP/ETH')
        if 0.00107 < data['open'] < 0.001078:
            self.exchange_api.place_limit_order('XRP', 'ETH', 0.001078, 1000, OrderSide.Buy)
        else:
            available = self.exchange_api.get_balance()['XRP']['total'] - \
                        self.exchange_api.get_balance()['XRP']['in_order']
            if available > 0:
                print("Available", available)
                self.exchange_api.place_limit_order('XRP', 'ETH', 0.001078, available, OrderSide.Sell)
        self.display_balance()