import unittest

from backtest.Errors import NotSupported, InsufficientFunds, InvalidOrder, OrderNotFound, SlippageModelError
from backtest.BackExchange import BackExchange
from core.Quote import batch_quotes_csv_reader
from core.Timer import Timer


class BackExchangeTest(unittest.TestCase):
    def setUp(self):
        file_path = '../data/binance/'
        start_time = 1517599560000
        end_time = 1517604900000
        step = 60 * 1000

        self.timer = Timer(start_time, end_time, step)
        self.ex = BackExchange(timer=self.timer,
                               quotes=batch_quotes_csv_reader(file_path))

    def assertDictContainsSubset(self, subset, dictionary, msg=None):
        actual = {k: v for k, v in dictionary.items() if k in subset}
        self.assertDictEqual(subset, actual)

    def forward_to_timestamp(self, timestamp):
        while self.timer.time < timestamp:
            self.timer.next()
        self.ex.process()

    def next_tickers(self, n: int):
        for i in range(n):
            self.timer.next()
        self.ex.process()

    def test_market_info(self):
        # fetch_timestamp
        self.assertEqual(self.ex.fetch_timestamp(), 1517599560000)

        # fetch_markets
        assets, symbols = self.ex.fetch_markets()
        self.assertSetEqual(assets, {'ETH', 'BTC', 'USDT', 'XRP'})
        self.assertSetEqual(symbols, {'XRP/ETH', 'ETH/USDT', 'ETH/BTC'})

        # fetch_ticker
        self.assertRaises(NotSupported, self.ex.fetch_ticker, 'XXX')
        self.assertDictEqual(self.ex.fetch_ticker('XRP/ETH'),
                             {'open': 0.00095494, 'high': 0.00095751, 'low': 0.00095293,
                              'close': 0.00095518, 'volume': 13013.0})

    def test_deposit_and_withdraw(self):
        # deposit
        self.assertEqual(self.ex.deposit('ETH', -10), 0)
        self.assertEqual(self.ex.deposit('ETH', 10), 10)

        self.next_tickers(1)
        self.ex.deposit('BTC', 5)

        # withdraw
        self.assertEqual(self.ex.withdraw('ETH', -3), 0)
        self.assertEqual(self.ex.withdraw('ETH', 3), -3)

        # fetch_balance
        self.assertDictEqual(self.ex.fetch_balance(),
                             {'BTC': {'free': 5, 'used': 0, 'total': 5},
                              'ETH': {'free': 7, 'used': 0, 'total': 7},
                              'USDT': {'free': 0, 'used': 0, 'total': 0},
                              'XRP': {'free': 0, 'used': 0, 'total': 0}})

        # fetch_deposit_history
        history = list()
        history.append({'timestamp': 1517599560000, 'asset': 'ETH', 'amount': 10})
        history.append({'timestamp': 1517599620000, 'asset': 'BTC', 'amount': 5})
        history.append({'timestamp': 1517599620000, 'asset': 'ETH', 'amount': -3})
        self.assertListEqual(self.ex.fetch_deposit_history(), history)

    def test_market_order(self):
        # create_market_buy_order
        order_info1 = self.ex.create_market_buy_order(symbol='XRP/ETH', amount=100)
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'status': 'submitted', 'symbol': 'XRP/ETH',
                                       'type': 'market', 'side': 'buy', 'price': 0, 'amount': 100, 'filled': 0,
                                       'remaining': 100, 'transaction': [], 'fee': {}},
                                      order_info1)

        # fetch_submitted_order
        self.assertDictEqual(self.ex.fetch_submitted_order(order_info1['id']), order_info1)

        # create_market_sell_order
        order_info2 = self.ex.create_market_sell_order(symbol='XRP/ETH', amount=10)

        # cancel_submitted_order
        self.ex.cancel_submitted_order(order_info2['id'])
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'status': 'cancelled', 'symbol': 'XRP/ETH',
                                       'type': 'market', 'side': 'sell', 'price': 0, 'amount': 10, 'filled': 0,
                                       'remaining': 10, 'transaction': [], 'fee': {}},
                                      self.ex.fetch_submitted_order(order_info2['id']))

        # fetch_submitted_orders
        orders = self.ex.fetch_submitted_orders()
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[0]['id'], order_info1['id'])
        self.assertEqual(orders[1]['id'], order_info2['id'])

        # InsufficientFunds
        self.assertRaises(InsufficientFunds, self.ex.process)

        # InvalidOrder
        self.next_tickers(1)
        self.assertRaises(InvalidOrder, self.ex.create_market_buy_order, symbol='XXX', amount=10)
        self.assertRaises(InvalidOrder, self.ex.create_market_buy_order, symbol='XRP/ETH', amount=-10)
        self.assertRaises(InvalidOrder, self.ex.create_market_buy_order, symbol='XRP/ETH', amount=0)

        # execution of market buy order
        # fetch_closed_orders
        self.ex.deposit('ETH', 100)
        order_info3 = self.ex.create_market_buy_order(symbol='XRP/ETH', amount=100)
        self.assertRaises(OrderNotFound, self.ex.fetch_closed_orders, symbol='XRP/ETH')

        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 0)
        closed_order = self.ex.fetch_closed_orders(symbol='XRP/ETH')
        self.assertEqual(len(closed_order), 1)
        self.assertDictContainsSubset({'timestamp': 1517599620000, 'id': order_info3['id'], 'status': 'filled',
                                       'symbol': 'XRP/ETH', 'type': 'market', 'side': 'buy', 'price': 0,
                                       'amount': 100, 'filled': 100, 'remaining': 0, 'fee': {'XRP': 0.05}},
                                      closed_order[0])
        self.assertEqual(len(closed_order[0]['transaction']), 1)
        self.assertDictContainsSubset({'timestamp': 1517599680000, 'price': 0.00095605, 'amount': 100},
                                      closed_order[0]['transaction'][0])
        self.assertDictEqual(self.ex.fetch_balance()['ETH'], {'free': 99.904395, 'used': 0, 'total': 99.904395})
        self.assertDictEqual(self.ex.fetch_balance()['XRP'], {'free': 99.95, 'used': 0, 'total': 99.95})

        self.next_tickers(5)

        # execution of market sell order
        order_info4 = self.ex.create_market_sell_order(symbol='XRP/ETH', amount=80)
        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 0)
        closed_order = self.ex.fetch_closed_orders(symbol='XRP/ETH')
        self.assertEqual(len(closed_order), 2)
        self.assertDictContainsSubset({'timestamp': 1517599980000, 'id': order_info4['id'], 'status': 'filled',
                                       'symbol': 'XRP/ETH', 'type': 'market', 'side': 'sell', 'price': 0,
                                       'amount': 80, 'filled': 80, 'remaining': 0, 'fee': {'ETH': 0.00003884}},
                                      closed_order[1])
        self.assertEqual(len(closed_order[1]['transaction']), 1)
        self.assertDictContainsSubset({'timestamp': 1517600040000, 'price': 0.0009709, 'amount': 80},
                                      closed_order[1]['transaction'][0])
        self.assertDictEqual(self.ex.fetch_balance()['ETH'], {'free': 99.98202816, 'used': 0, 'total': 99.98202816})
        self.assertDictEqual(self.ex.fetch_balance()['XRP'], {'free': 19.95, 'used': 0, 'total': 19.95})

    def test_list_and_delist(self):
        # newly list
        self.forward_to_timestamp(1517601360000)
        self.assertEqual(self.ex.fetch_timestamp(), 1517601360000)
        assets, symbols = self.ex.fetch_markets()
        self.assertSetEqual(assets, {'ETH', 'BTC', 'USDT', 'XRP', 'NANO'})
        self.assertSetEqual(symbols, {'XRP/ETH', 'ETH/USDT', 'ETH/BTC', 'NANO/BTC', 'NANO/ETH'})

        # delist
        self.forward_to_timestamp(1517603700000)
        self.assertEqual(self.ex.fetch_timestamp(), 1517603700000)
        assets, symbols = self.ex.fetch_markets()
        self.assertSetEqual(assets, {'ETH', 'BTC', 'USDT', 'XRP'})
        self.assertSetEqual(symbols, {'XRP/ETH', 'ETH/USDT', 'ETH/BTC'})

        # need to add:
        # order, balance


if __name__ == '__main__':
    unittest.main()
