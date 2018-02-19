"""
This file implements the basic I/O operations for an asset
1, Read Asset Data from CSV files with path specified
2, Read Asset Data from a given URL, or external APIs whose interfaces are predefined
3, Get price data for a given time (day, minute)
"""

import os
import csv

import pandas as pd

from enum import Enum


class QuoteFields(Enum):
    High = "high"
    Low = "low"
    Open = "open"
    Close = "close"
    Volume = "volume"


class QuoteReadMode(Enum):
    CSV = "csv"
    URL = "url"
    API = "api"


"""
The base class for quote
"""


class QuoteBase(object):
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

    def read_from_csv(self, file_path):
        raise NotImplementedError

    def read_from_url(self, url):
        raise NotImplementedError

    def read_from_api(self, api_fun):
        raise NotImplementedError

    def get_value(self, timestamp, field):
        raise NotImplementedError

    def price_high(self, timestamp):
        return self.get_value(timestamp, QuoteFields.High)

    def price_low(self, timestamp):
        return self.get_value(timestamp, QuoteFields.Low)

    def price_open(self, timestamp):
        return self.get_value(timestamp, QuoteFields.Open)

    def price_close(self, timestamp):
        return self.get_value(timestamp, QuoteFields.Close)

    def volume(self, timestamp):
        return self.get_value(timestamp, QuoteFields.Volume)

    def ohlcv(self, timestamp):
        return {'open': self.price_open(timestamp), 'high': self.price_high(timestamp),
                'low': self.price_low(timestamp), 'close': self.price_close(timestamp),
                'volume': self.volume(timestamp)}


"""
Quote class using CSV readers
"""


class QuoteCSV(QuoteBase):
    def __init__(self, quote_name, base_name, file_path):
        super(QuoteCSV, self).__init__(quote_name, base_name)
        self.read_from_csv(file_path)

    def read_from_csv(self, file_path):
        assert os.path.exists(file_path), "csv path : " + file_path + " does not exist."
        # basic checks for cvs format
        with open(file_path) as input_file:
            reader = csv.reader(input_file, delimiter=',')
            # data format: time_stamp and OHLCV, open, high, low, close, volume
            for each in reader:
                assert len(set(each) - {"timestamp", "open", "high", "low", "close", "volume"}) == 0 or \
                       len(set(each) - {"timestamp", "open", "high", "low", "closing", "volume"}) == 0, \
                    "format error for CSV dataset header, it has to be 6 cols:  timestamp + OHLCV"
                break
        pd_data = pd.read_csv(file_path)
        # use timestamp as primary key
        self._data = pd_data.set_index("timestamp")
        print("Read " + str(self._data.size) + " lines of price data for quote " + self._symbol)

    def get_value(self, timestamp, field):
        # field has to be the Asset
        assert isinstance(field, QuoteFields), "invalid field id: " + field
        if self._data is None:
            raise ValueError("Asset data is None and it has not been properly initialized.")
        try:
            return self._data.loc[timestamp, field.value]
        except Exception:
            raise KeyError(str(timestamp) + " or " + field.value + " does not exist in Asset's data")


class Quotes(object):
    def __init__(self):
        self._quotes = {}
        
    def __getitem__(self, name: str):
        return self.get_quote(name)

    def __iter__(self):
        return iter(self._quotes)

    def get_quote(self, name: str):
        try:
            return self._quotes[name]
        except KeyError:
            raise Exception("Asset not added yet. ")

    def add_quote(self, *, quote_name: str, base_name: str, mode: QuoteReadMode, extra_info):
        symbol = quote_name + '/' + base_name
        assert isinstance(mode, QuoteReadMode), "mode has to be a valid AssetReadMode"
        if mode is QuoteReadMode.CSV:
            if symbol in self._quotes:
                print("asset %s has been already added, now overwritten".format(symbol))
            # extra_info has to be a file path for CSVs
            self._quotes[symbol] = QuoteCSV(quote_name, base_name, extra_info)
        else:
            raise NotImplementedError

    def get_symbols(self):
        return self._quotes.keys()

    def get_assets(self):
        assets = set()
        for quote in self._quotes:
            assets.add(self._quotes[quote].quote_name)
            assets.add(self._quotes[quote].base_name)
        return assets


def batch_quotes_csv_reader(directory_name: str) -> Quotes:
    """
    generalization
    """
    quotes = Quotes()
    for file in os.listdir(directory_name):
        if file.endswith(".csv"):
            flist = file.translate({ord(c): ' ' for c in '-_,.'}).split()
            if len(flist) == 3:
                # correctly split format
                quotes.add_quote(quote_name=flist[0],
                                 base_name=flist[1],
                                 mode=QuoteReadMode.CSV,
                                 extra_info=directory_name + file)
            else:
                # attempt to deduce base currency
                if flist[0][-3:] in {'ETH', 'BTC', 'BNB'}:
                    quotes.add_quote(quote_name=flist[0][:-3],
                                     base_name=flist[0][-3:],
                                     mode=QuoteReadMode.CSV,
                                     extra_info=directory_name + file)
                elif flist[0][-4:] in {'USDT'}:
                    quotes.add_quote(quote_name=flist[0][:-4],
                                     base_name=flist[0][-4:],
                                     mode=QuoteReadMode.CSV,
                                     extra_info=directory_name + file)
                else:
                    print("Not able to parse " + file)

    return quotes

