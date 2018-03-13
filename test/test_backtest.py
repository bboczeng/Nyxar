import unittest

from backtest.Errors import NotSupported, InsufficientFunds, InvalidOrder
from backtest.BackExchange import BackExchange
from backtest.Slippage import VolumeSlippage, SpreadSlippage
from core.Ticker import Quotes, BidAsks
from core.Timer import Timer


class BackExchangeBlackBoxTest(unittest.TestCase):
    def setUp(self):
        file_path = '../data/binance/'
        start_time = 1517599560000
        end_time = 1517604900000
        step = 60 * 1000

        quotes = Quotes()
        quotes.add_tickers_csv(file_path)
        self.timer = Timer(start_time, end_time, step)
        self.ex = BackExchange(timer=self.timer, quotes=quotes)

    def assertDictContainsSubset(self, subset, dictionary, msg=None):
        actual = {k: v for k, v in dictionary.items() if k in subset}
        self.assertDictEqual(subset, actual)

    def forward_to_timestamp(self, timestamp):
        while self.timer.time < timestamp:
            self.timer.next()
            self.ex._process()

    def next_tickers(self, n: int):
        for i in range(n):
            self.timer.next()
            self.ex._process()

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
        self.assertEqual(self.ex.withdraw('ETH', 3), 3)

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

    def test_balance_in(self):
        self.forward_to_timestamp(1517601660000)
        self.ex.deposit('ETH', 10)
        self.ex.deposit('NANO', 10)
        self.ex.deposit('XRP', 10)

        self.assertEqual(self.ex.fetch_balance_in('ETH'), 10.2430411)
        self.assertEqual(self.ex.fetch_balance_in('ETH', True), 10.24291958)

        self.assertEqual(self.ex.fetch_balance_in('XRP'), 10668.61203404)
        self.assertEqual(self.ex.fetch_balance_in('XRP', True), 10663.16121940)

        self.assertEqual(self.ex.fetch_balance_in('BTC'), 1.06091274)
        self.assertEqual(self.ex.fetch_balance_in('BTC', True), 1.06036970)

        self.assertEqual(self.ex.fetch_balance_in('USDT'), 9233.07724754)
        self.assertEqual(self.ex.fetch_balance_in('USDT', True), 9228.35122506)

    def test_market_order(self):
        # create_market_buy_order
        order_info1 = self.ex.create_market_buy_order(symbol='XRP/ETH', amount=100)
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'status': 'submitted', 'symbol': 'XRP/ETH',
                                       'type': 'market', 'side': 'buy', 'price': 0, 'stop_price': 0, 'amount': 100,
                                       'filled': 0, 'remaining': 100, 'transaction': [], 'fee': {}},
                                      order_info1)

        # fetch_submitted_order
        self.assertDictEqual(self.ex.fetch_submitted_order(order_info1['id']), order_info1)

        # create_market_sell_order
        order_info2 = self.ex.create_market_sell_order(symbol='XRP/ETH', amount=10)

        # cancel_submitted_order
        self.ex.cancel_submitted_order(order_info2['id'])
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'status': 'cancelled', 'symbol': 'XRP/ETH',
                                       'type': 'market', 'side': 'sell', 'price': 0, 'stop_price': 0,
                                       'amount': 10, 'filled': 0, 'remaining': 10, 'transaction': [], 'fee': {}},
                                      self.ex.fetch_submitted_order(order_info2['id']))

        # fetch_submitted_orders
        orders = self.ex.fetch_submitted_orders()
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[0]['id'], order_info1['id'])
        self.assertEqual(orders[1]['id'], order_info2['id'])

        # InsufficientFunds
        self.assertRaises(InsufficientFunds, self.next_tickers, 1)

        # InvalidOrder
        self.assertRaises(InvalidOrder, self.ex.create_market_buy_order, symbol='XXX', amount=10)
        self.assertRaises(InvalidOrder, self.ex.create_market_buy_order, symbol='XRP/ETH', amount=-10)
        self.assertRaises(InvalidOrder, self.ex.create_market_buy_order, symbol='XRP/ETH', amount=0)

        # execution of market buy order
        # fetch_closed_orders
        self.ex.deposit('ETH', 100)
        order_info3 = self.ex.create_market_buy_order(symbol='XRP/ETH', amount=100)
        self.assertListEqual(self.ex.fetch_closed_orders(symbol='XRP/ETH'), [])

        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 0)
        closed_order = self.ex.fetch_closed_orders(symbol='XRP/ETH')
        self.assertEqual(len(closed_order), 1)
        self.assertDictContainsSubset({'timestamp': 1517599620000, 'id': order_info3['id'], 'status': 'filled',
                                       'symbol': 'XRP/ETH', 'type': 'market', 'side': 'buy', 'price': 0,
                                       'stop_price': 0, 'amount': 100, 'filled': 100, 'remaining': 0,
                                       'fee': {'XRP': 0.05}},
                                      closed_order[0])
        self.assertEqual(len(closed_order[0]['transaction']), 1)
        self.assertDictContainsSubset({'timestamp': 1517599680000, 'price': 0.00095605, 'amount': 100},
                                      closed_order[0]['transaction'][0])
        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.904395, 'used': 0, 'total': 99.904395})
        self.assertDictEqual(balance['XRP'], {'free': 99.95, 'used': 0, 'total': 99.95})

        self.next_tickers(5)

        # execution of market sell order
        order_info4 = self.ex.create_market_sell_order(symbol='XRP/ETH', amount=80)
        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 0)
        closed_order = self.ex.fetch_closed_orders(symbol='XRP/ETH')
        self.assertEqual(len(closed_order), 2)
        self.assertDictContainsSubset({'timestamp': 1517599980000, 'id': order_info4['id'], 'status': 'filled',
                                       'symbol': 'XRP/ETH', 'type': 'market', 'side': 'sell', 'price': 0,
                                       'stop_price': 0, 'amount': 80, 'filled': 80, 'remaining': 0,
                                       'fee': {'ETH': 0.00003884}},
                                      closed_order[1])
        self.assertEqual(len(closed_order[1]['transaction']), 1)
        self.assertDictContainsSubset({'timestamp': 1517600040000, 'price': 0.0009709, 'amount': 80},
                                      closed_order[1]['transaction'][0])
        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.98202816, 'used': 0, 'total': 99.98202816})
        self.assertDictEqual(balance['XRP'], {'free': 19.95, 'used': 0, 'total': 19.95})

    def test_limit_order(self):
        self.ex.deposit('ETH', 100)
        # create_limit_buy_order
        order_info1 = self.ex.create_limit_buy_order(symbol='XRP/ETH', amount=100, price=0.000954)
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'status': 'submitted', 'symbol': 'XRP/ETH',
                                       'type': 'limit', 'side': 'buy', 'price': 0.000954, 'stop_price': 0,
                                       'amount': 100, 'filled': 0, 'remaining': 100, 'transaction': [], 'fee': {}},
                                      order_info1)
        # fetch_submitted_order
        self.assertDictEqual(self.ex.fetch_submitted_order(order_info1['id']), order_info1)

        self.next_tickers(1)
        # fetch_open_orders
        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0]['status'], 'open')

        # create_market_sell_order
        order_info2 = self.ex.create_limit_sell_order(symbol='ETH/USDT', amount=10, price=886.0)
        self.assertDictContainsSubset({'timestamp': 1517599620000, 'status': 'submitted', 'symbol': 'ETH/USDT',
                                       'type': 'limit', 'side': 'sell', 'price': 886.0, 'stop_price': 0,
                                       'amount': 10, 'filled': 0, 'remaining': 10, 'transaction': [], 'fee': {}},
                                      order_info2)

        # fetch_submitted_orders
        orders = self.ex.fetch_submitted_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['id'], order_info2['id'])

        # InvalidOrder
        self.next_tickers(1)
        self.assertRaises(InvalidOrder, self.ex.create_limit_buy_order, symbol='XXX', amount=10, price=5)
        self.assertRaises(InvalidOrder, self.ex.create_limit_buy_order, symbol='XRP/ETH', amount=-10, price=5)
        self.assertRaises(InvalidOrder, self.ex.create_limit_buy_order, symbol='XRP/ETH', amount=0, price=5)
        self.assertRaises(InvalidOrder, self.ex.create_limit_buy_order, symbol='XRP/ETH', amount=10, price=-5)
        self.assertRaises(InvalidOrder, self.ex.create_limit_buy_order, symbol='XRP/ETH', amount=10, price=0)

        # fetch_open_orders
        orders = self.ex.fetch_open_orders()
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[0]['id'], order_info1['id'])
        self.assertEqual(orders[1]['id'], order_info2['id'])

        # in order balance
        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 89.9046, 'used': 10.0954, 'total': 100})
        self.assertDictEqual(balance['XRP'], {'free': 0, 'used': 0, 'total': 0})
        self.assertDictEqual(balance['USDT'], {'free': 0, 'used': 0, 'total': 0})

        # InsufficientFunds
        self.next_tickers(1)
        self.ex.create_limit_buy_order(symbol='ETH/BTC', amount=10, price=10)
        self.assertRaises(InsufficientFunds, self.next_tickers, 1)
        orders = self.ex.fetch_open_orders()
        self.assertEqual(len(orders), 2)

        # execution of limit sell order
        self.forward_to_timestamp(1517599920000)

        orders = self.ex.fetch_open_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['id'], order_info1['id'])

        closed_order = self.ex.fetch_closed_orders(symbol='ETH/USDT')
        self.assertEqual(len(closed_order), 1)
        self.assertDictContainsSubset({'timestamp': 1517599620000, 'id': order_info2['id'], 'status': 'filled',
                                       'symbol': 'ETH/USDT', 'type': 'limit', 'side': 'sell', 'price': 886.0,
                                       'stop_price': 0, 'amount': 10, 'filled': 10, 'remaining': 0,
                                       'fee': {'USDT': 4.43}},
                                      closed_order[0])
        self.assertEqual(len(closed_order[0]['transaction']), 1)
        self.assertDictContainsSubset({'timestamp': 1517599860000, 'price': 886.0, 'amount': 10},
                                      closed_order[0]['transaction'][0])

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 89.9046, 'used': 0.0954, 'total': 90})
        self.assertDictEqual(balance['XRP'], {'free': 0, 'used': 0, 'total': 0})
        self.assertDictEqual(balance['USDT'], {'free': 8855.57, 'used': 0, 'total': 8855.57})

        # execution of limit buy order
        self.forward_to_timestamp(1517604300000)

        self.assertEqual(len(self.ex.fetch_open_orders()), 0)

        closed_order = self.ex.fetch_closed_orders(symbol='XRP/ETH')
        self.assertEqual(len(closed_order), 1)
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'id': order_info1['id'], 'status': 'filled',
                                       'symbol': 'XRP/ETH', 'type': 'limit', 'side': 'buy', 'price': 0.000954,
                                       'stop_price': 0, 'amount': 100, 'filled': 100, 'remaining': 0,
                                       'fee': {'XRP': 0.05}},
                                      closed_order[0])
        self.assertEqual(len(closed_order[0]['transaction']), 1)
        self.assertDictContainsSubset({'timestamp': 1517604240000, 'price': 0.00095367, 'amount': 100},
                                      closed_order[0]['transaction'][0])

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 89.904633, 'used': 0, 'total': 89.904633})
        self.assertDictEqual(balance['XRP'], {'free': 99.95, 'used': 0, 'total': 99.95})
        self.assertDictEqual(balance['USDT'], {'free': 8855.57, 'used': 0, 'total': 8855.57})

    def test_stop_limit_order(self):
        self.ex.deposit('ETH', 100)
        # create_limit_buy_order
        order_info1 = self.ex.create_stop_limit_buy_order(symbol='XRP/ETH', amount=100, price=0.000965,
                                                          stop_price=0.00097)
        self.assertDictContainsSubset({'timestamp': 1517599560000, 'status': 'submitted', 'symbol': 'XRP/ETH',
                                       'type': 'stop_limit', 'side': 'buy', 'price': 0.000965, 'stop_price': 0.00097,
                                       'amount': 100, 'filled': 0, 'remaining': 100, 'transaction': [], 'fee': {}},
                                      order_info1)

        # fetch_submitted_order
        self.assertDictEqual(self.ex.fetch_submitted_order(order_info1['id']), order_info1)

        self.forward_to_timestamp(1517599980000)
        # fetch_open_orders
        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0]['status'], 'accepted')

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.9035, 'used': 0.0965, 'total': 100})
        self.assertDictEqual(balance['XRP'], {'free': 0, 'used': 0, 'total': 0})

        # execution of stop limit buy order
        self.next_tickers(1)
        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0]['status'], 'open')

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.9035, 'used': 0.0965, 'total': 100})
        self.assertDictEqual(balance['XRP'], {'free': 0, 'used': 0, 'total': 0})

        self.forward_to_timestamp(1517600220000)
        # fetch_open_orders
        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 0)
        closed_orders = self.ex.fetch_closed_orders('XRP/ETH')
        self.assertEqual(len(closed_orders), 1)
        self.assertEqual(closed_orders[0]['status'], 'filled')

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.90398, 'used': 0, 'total': 99.90398})
        self.assertDictEqual(balance['XRP'], {'free': 99.95, 'used': 0, 'total': 99.95})

        self.forward_to_timestamp(1517600340000)
        # create_limit_sell_order
        order_info2 = self.ex.create_stop_limit_sell_order(symbol='XRP/ETH', amount=50, price=0.000961,
                                                           stop_price=0.00096301)
        self.assertDictContainsSubset({'timestamp': 1517600340000, 'status': 'submitted', 'symbol': 'XRP/ETH',
                                       'type': 'stop_limit', 'side': 'sell', 'price': 0.000961,
                                       'stop_price': 0.00096301, 'amount': 50, 'filled': 0, 'remaining': 50,
                                       'transaction': [], 'fee': {}},
                                      order_info2)
        # fetch_submitted_order
        self.assertDictEqual(self.ex.fetch_submitted_order(order_info2['id']), order_info2)

        self.forward_to_timestamp(1517601480000)
        # fetch_open_orders
        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 1)
        self.assertEqual(open_orders[0]['status'], 'accepted')

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.90398, 'used': 0, 'total': 99.90398})
        self.assertDictEqual(balance['XRP'], {'free': 49.95, 'used': 50, 'total': 99.95})

        # execution of stop limit sell order
        # fetch_open_orders
        self.next_tickers(2)
        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 0)
        closed_orders = self.ex.fetch_closed_orders('XRP/ETH')
        self.assertEqual(len(closed_orders), 2)
        self.assertEqual(closed_orders[1]['id'], order_info2['id'])

        balance = self.ex.fetch_balance()
        self.assertDictEqual(balance['ETH'], {'free': 99.95200598, 'used': 0, 'total': 99.95200598})
        self.assertDictEqual(balance['XRP'], {'free': 49.95, 'used': 0, 'total': 49.95})

    def test_list_and_delist(self):
        # newly list
        self.forward_to_timestamp(1517601360000)
        self.assertEqual(self.ex.fetch_timestamp(), 1517601360000)
        assets, symbols = self.ex.fetch_markets()
        self.assertSetEqual(assets, {'ETH', 'BTC', 'USDT', 'XRP', 'NANO'})
        self.assertSetEqual(symbols, {'XRP/ETH', 'ETH/USDT', 'ETH/BTC', 'NANO/BTC', 'NANO/ETH'})

        self.ex.deposit('NANO', 100)
        self.ex.deposit('ETH', 100)
        self.ex.create_limit_buy_order(symbol='NANO/ETH', amount=100, price=0.000001)

        # delist
        self.forward_to_timestamp(1517603700000)
        self.assertEqual(self.ex.fetch_timestamp(), 1517603700000)
        assets, symbols = self.ex.fetch_markets()
        self.assertSetEqual(assets, {'ETH', 'BTC', 'USDT', 'XRP'})
        self.assertSetEqual(symbols, {'XRP/ETH', 'ETH/USDT', 'ETH/BTC'})

        open_orders = self.ex.fetch_open_orders()
        self.assertEqual(len(open_orders), 0)
        self.assertTrue('NANO' not in self.ex.fetch_balance())


class SlippageModelBlackboxTest(unittest.TestCase):
    def setUp(self):
        file_path = '../data/binance/'
        start_time = 1517599560000
        end_time = 1517604900000
        step = 60 * 1000

        quotes = Quotes()
        quotes.add_tickers_csv(file_path)
        self.timer = Timer(start_time, end_time, step)
        self.ex = BackExchange(timer=self.timer, quotes=quotes)

    def forward_to_timestamp(self, timestamp):
        while self.timer.time < timestamp:
            self.timer.next()
            self.ex._process()

    def next_tickers(self, n: int):
        for i in range(n):
            self.timer.next()
            self.ex._process()

    def test_volume_slippage(self):
        self.ex.slippage_model = VolumeSlippage()
        self.ex.deposit('ETH', 100)

        # buy slippage
        order = self.ex.create_limit_buy_order('XRP/ETH', 500, 0.1)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_order(order['id'])['filled'], 155.55)
        self.assertEqual(self.ex.fetch_balance()['ETH']['total'], 99.85129576)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_order(order['id'])['filled'], 413.55)
        self.assertEqual(self.ex.fetch_balance()['ETH']['total'], 99.60463486)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_order(order['id'])['status'], 'filled')

        # sell slippage
        order = self.ex.create_limit_sell_order('ETH/USDT', 7, 0.1)
        print(order)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_order(order['id'])['filled'], 1.78323325)
        self.assertEqual(self.ex.fetch_balance()['ETH']['total'], 97.73867328)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_order(order['id'])['filled'], 4.52946725)
        self.assertEqual(self.ex.fetch_balance()['ETH']['total'], 94.99243928)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_order(order['id'])['status'], 'filled')

        # market order is not affected
        # not used: order = self.ex.create_market_buy_order('XRP/ETH', 500)
        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 0)

    def test_spread_slippage(self):
        bidask_path = '../data/'
        bidask = BidAsks()
        bidask.add_tickers_csv(bidask_path)
        self.ex.slippage_model = SpreadSlippage(bidask)

        self.ex.deposit('ETH', 100)

        order = self.ex.create_limit_buy_order('XRP/ETH', 100, 0.000955)
        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 1)
        self.ex.cancel_open_order(order['id'])

        # buy slippage
        self.ex.create_limit_buy_order('XRP/ETH', 100, 0.1)
        self.next_tickers(1)
        # the order should be executed at (price + 0.5 * spread)
        # the actual value should be 0.0095701, however there is a float precision loss here
        self.assertEqual(self.ex.fetch_closed_orders('XRP/ETH')[1]['transaction'][0]['price'], 0.00095700)

        # sell slippage
        self.ex.create_limit_sell_order('XRP/ETH', 50, 0.0009569)
        # if no spread slippage, the order should already be filled at this timestamp
        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 1)
        self.next_tickers(1)
        self.assertEqual(self.ex.fetch_closed_orders('XRP/ETH')[2]['transaction'][0]['price'], 0.0009569)

        # this symbol doesn't have bidask data, should be executed at normal price
        self.ex.create_limit_sell_order('ETH/BTC', 50, 0.102735)
        self.next_tickers(1)
        self.assertEqual(len(self.ex.fetch_open_orders()), 0)


if __name__ == '__main__':
    unittest.main()
