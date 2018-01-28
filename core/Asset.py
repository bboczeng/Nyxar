
"""
This file implements the basic I/O operations for an asset
1, Read Asset Data from CSV files with path specified
2, Read Asset Data from a given URL, or external APIs whose interfaces are predefined
3, Get price data for a given time (day, minute)
"""

import os
from enum import Enum

class AssetFields(Enum):
    High = 0
    Low = 1
    Open = 2
    Close = 3
    Volume = 4


class AssetBase(object):

    field_names = {
        AssetFields.High: "high",
        AssetFields.Low: "low",
        AssetFields.Open: "open",
        AssetFields.Close: "close",
        AssetFields.Volume: "volume",
    }

    def __init__(self):
        pass

    def read_from_csv(self, file_path):
        assert os.path.exists(file_path), "csv path : " + file_path + " does not exist."
        # implement the reading algorithm

    def read_from_url(self, url):
        pass

    def read_from_api(self, api_fun):
        pass

    def __get_value(self, index, field):
        ## implement in subclass
        pass

    @property
    def price_high(self, index):
        return self.__get_value(index, self.__class__.field_names[AssetFields.High])

    @property
    def price_low(self, index):
        return self.__get_value(index, self.__class__.field_names[AssetFields.Low])

    @property
    def price_open(self, index):
        return self.__get_value(index, self.__class__.field_names[AssetFields.Open])

    @property
    def price_close(self, index):
        return self.__get_value(index, self.__class__.field_names[AssetFields.Close])

    @property
    def price_volume(self, index):
        return self.__get_value(index, self.__class__.field_names[AssetFields.Volume])