
"""
This file implements the basic I/O operations for an asset
1, Read Asset Data from CSV files with path specified
2, Read Asset Data from a given URL, or external APIs whose interfaces are predefined
3, Get price data for a given time (day, minute)
"""

import os
import csv

from enum import Enum

class AssetFields(Enum):
    High = 0
    Low = 1
    Open = 2
    Close = 3
    Volume = 4


"""
The base class for asset
"""

class AssetBase(object):

    def __init__(self, name):
        self.name = name
        self.data = {}

    def read_from_csv(self, file_path):
        pass

    def read_from_url(self, url):
        pass

    def read_from_api(self, api_fun):
        pass

    def __get_value(self, index, field):
        pass

    @property
    def price_high(self, index):
        return self.__get_value(index, AssetFields.High)

    @property
    def price_low(self, index):
        return self.__get_value(index, AssetFields.Low)

    @property
    def price_open(self, index):
        return self.__get_value(index, AssetFields.Open)

    @property
    def price_close(self, index):
        return self.__get_value(index, AssetFields.Close)

    @property
    def price_volume(self, index):
        return self.__get_value(index, AssetFields.Volume)


"""
Asset class for 
"""

class AssetCSV(AssetBase):
    def __init__(self, name, file_path):
        super(AssetCSV, self).__init__(name)
        self.file_path = file_path
        # read data
        self.data = self.read_from_csv(file_path)

    def read_from_csv(self, file_path):
        assert os.path.exists(file_path), "csv path : " + file_path + " does not exist."
        # implement the reading algorithm
        with open(file_path) as input_file:
            reader = csv.reader(input_file, delimiter=',')
            count = 0
            # data format: time_stamp and OHLC, open, high, low, close,
            for each in reader:
                assert len(each) == 5, "format error for CSV dataset, it has to be timestamp + OHLC"
                if count == 0:
                    count += 1
                    continue
                time_stamp = each[0]
                price_data = {
                    AssetFields.Open: float(each[1]),
                    AssetFields.High: float(each[2]),
                    AssetFields.Low: float(each[3]),
                    AssetFields.Close: float(each[4])}
                self.data[time_stamp] = price_data

    def __get_value(self, index, field):
        assert isinstance(field, AssetFields), "invalid field id: " + field
        if index not in self.data:
            raise KeyError("timestamp index: " + index + "does not exist for asset " + self.name)
        return self.data[index][field]
