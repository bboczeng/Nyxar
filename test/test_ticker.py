import unittest
import re
from backtest.Errors import NotSupported, InsufficientFunds, InvalidOrder, OrderNotFound, SlippageModelError
from backtest.BackExchange import BackExchange
from backtest.Slippage import VolumeSlippage, SpreadSlippage
from core.Ticker import Quotes, BidAsks
from core.Timer import Timer

class Ticker(unittest.TestCase):
    def setUp(self):
        pass

    def test_csv_ticker(self):
        file_path = '../data/binance/'
        quotes = Quotes()
        quotes.add_tickers_csv(file_path)
        self.assertEqual(len(quotes), 5)

        quotes = Quotes()
        quotes.add_tickers_csv(file_path, '(\w+)-(USDT).csv')
        self.assertEqual(len(quotes), 1)

        file_path = '../data/'
        bidasks = BidAsks()
        bidasks.add_tickers_csv(file_path)
        self.assertEqual(len(bidasks), 1)

    def test_exchange_ticker(self):
        quotes = Quotes()
        quotes.add_tickers_exchange('binance', pattern='(\w+)/(USDT)')
        self.assertEqual(len(quotes), 6) # this may change with time


if __name__ == '__main__':
    unittest.main()
