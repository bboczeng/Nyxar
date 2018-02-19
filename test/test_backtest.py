import unittest

#from backtest.Errors import NotSupported, InsufficientFunds, InvalidOrder, OrderNotFound, SlippageModelError
from backtest.BackExchange import BackExchange
from core.Quote import batch_quotes_csv_reader
from core.Timer import Timer

import backtest.Errors


class BackExchangeTest(unittest.TestCase):
    def setUp(self):
        file_path = '../data/binance/'
        start_time = 1517599560000
        end_time = 1517604900000
        step = 60 * 1000

        self.timer = Timer(start_time, end_time, step)
        self.ex = BackExchange(timer=self.timer,
                               quotes=batch_quotes_csv_reader(file_path))

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
        self.assertRaises(backtest.Errors.NotSupported, self.ex.fetch_ticker, 'XXX')
        self.assertDictEqual(self.ex.fetch_ticker('XRP/ETH'),
                             {'open': 0.00095494, 'high': 0.00095751,
                              'low': 0.00095293, 'close': 0.00095518, 'volume': 13013.0})

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
                             {'BTC': {'available': 5, 'in order': 0, 'total': 5},
                              'ETH': {'available': 7, 'in order': 0, 'total': 7},
                              'USDT': {'available': 0, 'in order': 0, 'total': 0},
                              'XRP': {'available': 0, 'in order': 0, 'total': 0}})

        # fetch_deposit_history
        history = list()
        history.append({'timestamp': 1517599560000, 'asset': 'ETH', 'amount': 10})
        history.append({'timestamp': 1517599620000, 'asset': 'BTC', 'amount': 5})
        history.append({'timestamp': 1517599620000, 'asset': 'ETH','amount': -3})
        self.assertListEqual(self.ex.fetch_deposit_history(), history)

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
