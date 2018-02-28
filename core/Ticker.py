import os
import csv
import pandas as pd

from enum import Enum
# from decimal import *
# getcontext().prec = 8


class TickerFields(Enum):
    High = "high"
    Low = "low"
    Open = "open"
    Close = "close"
    Volume = "volume"
    Bid = "bid"
    Ask = "ask"
    Last = "last"


class TickerReadMode(Enum):
    CSV = "csv"
    URL = "url"
    API = "api"


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

    def read_from_csv(self, file_path: str, field_name: list):
        raise NotImplementedError

    def read_from_url(self, url: str):
        raise NotImplementedError

    def read_from_api(self, api_fun):
        raise NotImplementedError

    def get_value(self, timestamp: int, field: TickerFields):
        raise NotImplementedError


class TickerCSV(TickerBase):
    def __init__(self, quote_name: str, base_name: str, file_path: str, field_name: list):
        super(TickerCSV, self).__init__(quote_name, base_name)
        self.read_from_csv(file_path, field_name)

    def read_from_csv(self, file_path: str, field_name: list):
        assert os.path.exists(file_path)
        assert "timestamp" in field_name

        with open(file_path) as input_file:
            reader = csv.reader(input_file)
            header = reader.__next__()
            if set(field_name) <= set(header):
                pd_data = pd.read_csv(file_path)
            elif len(header) == len(field_name):
                pd_data = pd.read_csv(file_path, names=field_name)
            else:
                raise ValueError

        # use timestamp as primary key
        self._data = pd_data.set_index("timestamp")

        print("[Ticker] Read {:d} lines of ticker data for {:s}".format(self._data.shape[0], self._symbol))

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


class QuoteBase(TickerBase):
    def __init__(self, quote_name: str, base_name: str):
        super(QuoteBase, self).__init__(quote_name, base_name)

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


class BidAskBase(TickerBase):
    def __init__(self, quote_name: str, base_name: str):
        super(BidAskBase, self).__init__(quote_name, base_name)

    def price_bid(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Bid)

    def price_ask(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Ask)

    def price_last(self, timestamp: int):
        return self.get_value(timestamp, TickerFields.Last)


class QuoteCSV(TickerCSV, QuoteBase):
    def __init__(self, quote_name: str, base_name: str, file_path: str):
        super(QuoteCSV, self).__init__(quote_name, base_name, file_path,
                                       ['timestamp', 'open', 'high', 'low', 'close', 'volume'])


class BidAskCSV(TickerCSV, BidAskBase):
    def __init__(self, quote_name: str, base_name: str, file_path: str):
        super(BidAskCSV, self).__init__(quote_name, base_name, file_path,
                                        ['timestamp', 'bid', 'ask', 'last'])


class TickersBase(object):
    def __init__(self, ticker_type: str):
        self._tickers = {}
        self._ticker_type = ticker_type
        
    def __getitem__(self, name: str):
        return self.get_ticker(name)

    def __iter__(self):
        return iter(self._tickers)

    def get_ticker(self, name: str):
        try:
            return self._tickers[name]
        except KeyError:
            raise KeyError("Asset not added yet. ")

    def add_ticker(self, quote_name: str, base_name: str, mode: TickerReadMode, extra_info):
        assert isinstance(mode, TickerReadMode)
        symbol = quote_name + '/' + base_name
        if mode is TickerReadMode.CSV:
            if symbol in self._tickers:
                print("[Tickers] Asset {:s} has been already added, now overwritten. ".format(symbol))
            # extra_info has to be a file path for CSVs
            self._tickers[symbol] = globals()[self._ticker_type + "CSV"](quote_name, base_name, extra_info)
        else:
            raise NotImplementedError

    def get_symbols(self):
        return self._tickers.keys()

    def get_assets(self):
        assets = set()
        for quote in self._tickers:
            assets.add(self._tickers[quote].quote_name)
            assets.add(self._tickers[quote].base_name)
        return assets

    def add_tickers_csv(self, directory_name):
        for file in os.listdir(directory_name):
            if file.endswith(".csv"):
                flist = file.translate({ord(c): ' ' for c in '-_,.'}).split()
                if len(flist) == 3:
                    # correctly split format
                    self.add_ticker(quote_name=flist[0],
                                    base_name=flist[1],
                                    mode=TickerReadMode.CSV,
                                    extra_info=directory_name + file)
                else:
                    # attempt to deduce base currency
                    if flist[0][-3:] in {'ETH', 'BTC', 'BNB'}:
                        self.add_ticker(quote_name=flist[0][:-3],
                                        base_name=flist[0][-3:],
                                        mode=TickerReadMode.CSV,
                                        extra_info=directory_name + file)
                    elif flist[0][-4:] in {'USDT'}:
                        self.add_ticker(quote_name=flist[0][:-4],
                                        base_name=flist[0][-4:],
                                        mode=TickerReadMode.CSV,
                                        extra_info=directory_name + file)
                    else:
                        print("Not able to parse " + file)


class Quotes(TickersBase):
    def __init__(self):
        super(Quotes, self).__init__("Quote")


class BidAsks(TickersBase):
    def __init__(self):
        super(BidAsks, self).__init__("BidAsk")
