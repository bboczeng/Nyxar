import os
import csv
import pandas as pd
import re
import ccxt
import time

from enum import Enum
# from decimal import *
# getcontext().prec = 8

from ccxt.base.errors import ExchangeNotAvailable, ExchangeError, RequestTimeout, DDoSProtection


N_RETRY = 10
DDOS_COOLDOWN = 120


class TickerFields(Enum):
    High = "high"
    Low = "low"
    Open = "open"
    Close = "close"
    Volume = "volume"

    Bid = "bid"
    Ask = "ask"
    Last = "last"


class TickerBase(object):
    def __init__(self, quote_name: str, base_name: str):
        self._quote_name = quote_name
        self._base_name = base_name
        self._symbol = quote_name + "/" + base_name
        self._data = None

    @property
    def quote_name(self):
        return self._quote_name

    @property
    def base_name(self):
        return self._base_name

    @property
    def symbol(self):
        return self._symbol

    def read_from_csv(self, file_path: str, field_name: set):
        """
        Read fields given by field_name from a csv file file_path. If the CSV file already has a header, only columns
        with field name in field_name will be imported. If the CSV file doesn't have a header, the number of columns
        must equal the length of field_name, and columns will be interpreted as field names in field_name in order.

        Args:
            file_path: Path to CSV file.
            field_name: List of field names to import.
        """
        assert os.path.exists(file_path)
        assert "timestamp" in field_name

        pd_data = None

        with open(file_path) as input_file:
            reader = csv.reader(input_file)
            header = reader.__next__()
            if set(field_name) <= set(header):
                pd_data = pd.read_csv(file_path, usecols=field_name)
            elif len(header) == len(field_name):
                pd_data = pd.read_csv(file_path, names=field_name)
            else:
                raise ValueError

        if pd_data is None:
            raise ValueError
        # use timestamp as primary key
        self._data = pd_data.set_index("timestamp")

        print("[Ticker] Read {:d} lines of ticker data for {:s}".format(self._data.shape[0], self._symbol))

    def read_from_table(self, table: list, field_name: set):
        pd_data = pd.DataFrame(table, columns=field_name)
        # use timestamp as primary key
        self._data = pd_data.set_index("timestamp")
        print("[Ticker] Read {:d} lines of ticker data for {:s}".format(self._data.shape[0], self._symbol))

    def read_from_pandas(self, data_frame):
        if not isinstance(data_frame, pd.DataFrame):
            raise TypeError
        self._data = data_frame.set_index("timestamp")

    def read_from_url(self, url: str):
        raise NotImplementedError

    def read_from_api(self, api_fun):
        raise NotImplementedError

    def get_value(self, timestamp: int, field: TickerFields):
        assert isinstance(field, TickerFields)

        if self._data is None:
            raise ValueError
        try:
            return self._data.loc[timestamp, field.value]
        except Exception:
            raise KeyError

    def get_closet_value(self, timestamp: int, field: TickerFields):
        # It can actually be optimized further by shrinking search range, since time never travels back
        assert isinstance(field, TickerFields)

        idx = self._data.index.searchsorted(timestamp)
        if idx == len(self._data.index):
            idx -= 1
        elif idx > 0:
            if self._data.index[idx] - timestamp > timestamp - self._data.index[idx - 1]:
                idx -= 1
        return self._data.iloc[idx][field.value]


class Quote(TickerBase):
    def __init__(self, quote_name: str, base_name: str):
        super(Quote, self).__init__(quote_name, base_name)

    def price_high(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.High)

    def price_low(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Low)

    def price_open(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Open)

    def price_close(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Close)

    def volume(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Volume)

    def ohlcv(self, timestamp: int):
        return {'open': self.price_open(timestamp), 'high': self.price_high(timestamp),
                'low': self.price_low(timestamp), 'close': self.price_close(timestamp),
                'volume': self.volume(timestamp)}

    def read_from_csv(self, file_path: str, field_name=('timestamp', 'open', 'high', 'low', 'close', 'volume')):
        super(Quote, self).read_from_csv(file_path, field_name)

    def read_from_table(self, table: list, field_name=('timestamp', 'open', 'high', 'low', 'close', 'volume')):
        super(Quote, self).read_from_table(table, field_name)

    def read_from_url(self, url: str):
        raise NotImplementedError

    def read_from_api(self, api_fun):
        raise NotImplementedError


class BidAsk(TickerBase):
    def __init__(self, quote_name: str, base_name: str):
        super(BidAsk, self).__init__(quote_name, base_name)

    def price_bid(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Bid)

    def price_ask(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Ask)

    def price_last(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Last)

    def read_from_csv(self, file_path: str, field_name=('timestamp', 'bid', 'ask', 'last')):
        super(BidAsk, self).read_from_csv(file_path, field_name)

    def read_from_url(self, url: str):
        raise NotImplementedError

    def read_from_api(self, api_fun):
        raise NotImplementedError


class TickersBase(object):
    def __init__(self, ticker_type: str):
        self._tickers = {}
        self._ticker_type = ticker_type
        
    def __getitem__(self, name: str):
        return self.get_ticker(name)

    def __iter__(self):
        return iter(self._tickers)

    def __len__(self):
        return len(self._tickers)

    def get_ticker(self, name: str):
        try:
            return self._tickers[name]
        except KeyError:
            raise KeyError("Asset not added yet. ")

    def get_symbols(self):
        return self._tickers.keys()

    def get_assets(self):
        assets = set()
        for quote in self._tickers:
            assets.add(self._tickers[quote].quote_name)
            assets.add(self._tickers[quote].base_name)
        return assets

    def add_tickers_csv(self, directory_name: str, pattern: str='(\w+)[-.,_](\w+).csv'):
        for file in os.listdir(directory_name):
            match_obj = re.match(pattern, file)
            if match_obj:
                quote_name = match_obj.group(1)
                base_name = match_obj.group(2)
                symbol = quote_name + '/' + base_name
                if symbol in self._tickers:
                    print("[Tickers] Asset {:s} has been already added, now overwritten. ".format(symbol))
                # extra_info has to be a file path for CSVs
                self._tickers[symbol] = globals()[self._ticker_type](quote_name, base_name)
                self._tickers[symbol].read_from_csv(directory_name + file)
            else:
                print("[Ticker] Not able to parse " + file)


class Quotes(TickersBase):
    def __init__(self):
        super(Quotes, self).__init__("Quote")

    def add_tickers_exchange(self, exchange_name: str, timeframe: str='1d', pattern: str='(\w+)/(\w+)', path: str=''):
        exchange = getattr(ccxt, exchange_name)()
        if not exchange.has['fetchOHLCV']:
            print("Exchange doesn't support fetching OHLCV! ")
            return

        markets = exchange.loadMarkets()
        directory = ''
        if path != '':
            directory = path + exchange_name + '/'
            if not os.path.exists(directory):
                os.makedirs(directory)

        for symbol in markets:
            match_obj = re.match(pattern, symbol)
            if match_obj:
                quote_name = match_obj.group(1)
                base_name = match_obj.group(2)
                symbol = quote_name + '/' + base_name
                if symbol in self._tickers:
                    print("[Tickers] Asset {:s} has been already added, now overwritten. ".format(symbol))
                # extra_info has to be a file path for CSVs
                self._tickers[symbol] = Quote(quote_name, base_name)

                for attempt in range(N_RETRY):
                    try:
                        data_table = exchange.fetch_ohlcv(symbol, timeframe)
                        self._tickers[symbol].read_from_table(data_table)

                        if path != '':
                            filename = directory + symbol.translate({ord(c): '-' for c in '!@#$/'}) + '.csv'
                            with open(filename, 'a+', newline='') as file:
                                writer = csv.writer(file)
                                writer.writerow(['timestamp', 'open', 'high', 'low', 'closing', 'volume'])

                            with open(filename, 'a+', newline='') as file:
                                writer = csv.writer(file)
                                for row in range(len(data_table)):
                                    writer.writerow(data_table[row])
                            print("[Tickers] {:d} lines of ticker data {:s} saved to disk. ".format(len(data_table),
                                                                                                    symbol))

                    except ExchangeNotAvailable or ExchangeError or RequestTimeout:
                        print('[Tickers] Network error, retry ' + str(attempt + 1) + '/' + str(N_RETRY))
                        time.sleep(exchange.rateLimit / 1000)
                        continue
                    except DDoSProtection:
                        print('[Tickers] DDoS protection error, cool down ' + str(DDOS_COOLDOWN) + 's...')
                        time.sleep(DDOS_COOLDOWN)
                        continue
                    else:
                        break
                else:
                    print('[Tickers] Fail to load ticker ' + symbol)
                    continue

                time.sleep(exchange.rateLimit / 1000)
            else:
                print("[Ticker] Not able to parse " + symbol)


class BidAsks(TickersBase):
    def __init__(self):
        super(BidAsks, self).__init__("BidAsk")