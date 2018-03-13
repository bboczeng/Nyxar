from requests.exceptions import ReadTimeout

from api.errors import PathNotSpecified
from api.errors import TimestampError

import os
import csv
import time
import json
import requests


class CoinMarketCap:
    def __init__(self, path='', retry=5):
        self.data_source_name = 'coinmarketcap'
        self.base_url = 'https://api.coinmarketcap.com/v1/'
        self.path = path
        self.retry = retry
        self.timeout = 30

        # data cache
        self.last_volume = {}

        self.session = requests.session()

        if path != '':
            self.path = path + '/' + self.data_source_name + '/'
            if not os.path.exists(self.path):
                os.makedirs(self.path)

    def get(self, endpoint, params):
        for attempt in range(self.retry):
            try:
                response = self.session.get(self.base_url + endpoint, params=params, timeout=self.timeout)
            except ReadTimeout as exception:
                print('   ' + exception.__class__.__name__ + ', retry ' + str(attempt + 1) + '/' + str(self.retry))
                time.sleep(1)
                continue
            else:
                return json.loads(response.text)
        else:
            print('   Fail to get from: ' + self.base_url + '/' + endpoint)
            return

    """ TODO: fix, default params value is mutable """
    def fetch_volume(self, save=True, params={'start': 0, 'limit': 200}):
        def num(s):
            try:
                return int(s)
            except ValueError:
                return float(s)
            except TypeError:
                return None

        print("Fetching volume from " + self.data_source_name + "...")
        endpoint = '/ticker/'
        fieldnames = ['timestamp', 'rank', 'available_supply', 'market_cap_usd', '24h_volume_usd',
                      'percent_change_7d', 'percent_change_24h', 'percent_change_1h', 'price_usd', 'price_btc']

        data = self.get(endpoint, params)

        for data_dict in data:
            symbol = data_dict['symbol']
            self.last_volume[symbol] = {}
            for field in fieldnames:
                if field == 'timestamp':
                    self.last_volume[symbol]['timestamp'] = int(data_dict['last_updated']) * 1000    # to ms
                else:
                    self.last_volume[symbol][field] = num(data_dict[field])

            if save:
                if self.path == '':
                    raise PathNotSpecified("Path not specified for saving data. ")

                filename = self.path + data_dict['symbol'].translate({ord(c): '-' for c in '!@#$/'}) + '.csv'

                if os.path.exists(filename):
                    with open(filename, 'rb') as file:
                        file.seek(-2, os.SEEK_END)      # Jump to the second last byte
                        while file.read(1) != b"\n":    # Until EOL is found...
                            file.seek(-2, os.SEEK_CUR)  # ...jump back the read byte plus one more
                        last = file.readline()
                        last_timestamp_in_file = int(last.split(b",")[0])

                    if self.last_volume[symbol]['timestamp'] < last_timestamp_in_file:
                        raise TimestampError('It seems saved data is from the future. ')
                    elif self.last_volume[symbol]['timestamp'] > last_timestamp_in_file:
                        with open(filename, 'a+', newline='') as file:
                            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
                            writer.writerow(self.last_volume[symbol])

                else:
                    with open(filename, 'a+', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(fieldnames)

                        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writerow(self.last_volume[symbol])
