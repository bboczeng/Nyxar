
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


class AssetFields(Enum):
    High = "high"
    Low = "low"
    Open = "open"
    Close = "close"
    Volume = "volume"


"""
The base class for asset
"""


class AssetBase(object):

    def __init__(self, name):
        self.name = name
        self.data = None

    def read_from_csv(self, file_path):
        pass

    def read_from_url(self, url):
        pass

    def read_from_api(self, api_fun):
        pass

    def __get_value(self, timestamp, field):
        pass

    @property
    def price_high(self, timestamp):
        return self.__get_value(timestamp, AssetFields.High)

    @property
    def price_low(self, timestamp):
        return self.__get_value(timestamp, AssetFields.Low)

    @property
    def price_open(self, timestamp):
        return self.__get_value(timestamp, AssetFields.Open)

    @property
    def price_close(self, timestamp):
        return self.__get_value(timestamp, AssetFields.Close)

    @property
    def price_volume(self, timestamp):
        return self.__get_value(timestamp, AssetFields.Volume)


"""
Asset class using CSV readers
"""


class AssetCSV(AssetBase):
    def __init__(self, name, file_path):
        super(AssetCSV, self).__init__(name)
        # read data
        self.read_from_csv(file_path)

    def read_from_csv(self, file_path):
        assert os.path.exists(file_path), "csv path : " + file_path + " does not exist."
        # implement the reading algorithm
        # basic checks for cvs format
        with open(file_path) as input_file:
            reader = csv.reader(input_file, delimiter=',')
            # data format: time_stamp and OHLCV, open, high, low, close, volume
            for each in reader:
                assert len(set(each) - set("timestamp", "open", "high", "low", "close", "volume")) == 0, \
                    "format error for CSV dataset, it has to be 6 cols:  timestamp + OHLCV"
                break
            # finish header check
        pd_data = pd.read_csv(file_path)
        # use timestamp as primary key
        pd_data.set_index("timestamp")
        self.data = pd_data
        print("Reading " + str(pd_data.size) + " lines of price data for Asset " + self.name)

    def __get_value(self, timestamp, field):
        # field has to be the Asset
        assert isinstance(field, AssetFields), "invalid field id: " + field
        if self.data is None:
            raise ValueError("Asset data is None and it has not been properly initialized.")
        try:
            return self.data.loc[timestamp, field]
        except Exception:
            raise KeyError(timestamp + " or " + field + " does not exist in Asset's data")

