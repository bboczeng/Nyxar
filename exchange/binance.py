from ccxt.base.errors import ExchangeNotAvailable
from ccxt.base.errors import ExchangeError
from ccxt.base.errors import RequestTimeout
from ccxt.base.errors import DDoSProtection

import os
import csv
import ccxt
import time
import json
import base64

#TO DO:
#Finish fetch_bidask
#Extract particular symbol


class OldDataNotContinuous(Exception):
    pass


class PathNotSpecified(Exception):
    pass


class binance:
    def __init__(self, path='', retry=10, ddos_cooldown=120):
        self.exchange_name = 'binance'
        self.exchange = getattr(ccxt, self.exchange_name)()
        self.path = path
        self.retry = retry
        self.cooldown = ddos_cooldown

        self.last_OHLCV = {}
        self.last_bid_ask = []
        self.last_orderbook = {}

        self.directory = {'OHLCV': 'OHLCV', 'bidask': 'bidask', 'orderbook': 'orderbook'}
        for dir in self.directory:
            directory = path + self.exchange_name + '/' + self.directory[dir] + '/'
            if not os.path.exists(directory):
                os.makedirs(directory)

    def load_markets(self):
        for attempt in range(self.retry):
            try:
                self.exchange.loadMarkets()
            except (ExchangeNotAvailable, ExchangeError, RequestTimeout) as exception:
                print('   ' + exception.__class__.__name__ + ', retry ' + str(attempt + 1) + '/' + str(self.retry))
                time.sleep(self.exchange.rateLimit / 1000)
                continue
            except DDoSProtection:
                print('   DDoSProtection error, cool down ' + str(self.cooldown) + "s...")
                time.sleep(self.cooldown)
                continue
            else:
                return True
        else:
            print('   Fail to load market')
            return False

    def fetch_ohlcv(self, save = True):
        """
        Fetch last 500 minutes OHLCV data for all tradable pairs
        Should call it around every 450 minutes

        """

        print("Fetching OHLCV from " + self.exchange_name + "...")
        if not self.load_markets():
            return

        fieldnames = ['timestamp', 'open', 'high', 'low', 'closing', 'volume']
        directory = self.path + self.exchange_name + '/' + self.directory['OHLCV'] + '/'

        counter = 1
        for symbol in self.exchange.markets:
            print('    ' + str(counter) + '/' + str(len(self.exchange.markets)) + ' ' + symbol)
            for attempt in range(self.retry):
                try:
                    self.last_OHLCV[symbol] = self.exchange.fetch_ohlcv(symbol, '1m')
                except (ExchangeNotAvailable, ExchangeError, RequestTimeout) as exception:
                    print('   ' + exception.__class__.__name__ + ', retry ' + str(attempt + 1) + '/' + str(self.retry))
                    time.sleep(self.exchange.rateLimit / 1000)
                    continue
                except DDoSProtection:
                    print('   DDoSProtection error, cool down ' + str(self.cooldown) + "s...")
                    time.sleep(self.cooldown)
                    continue
                else:
                    break
            else:
                print('   Fail to load OHLCV ' + symbol)
                continue

            if save:
                if self.path == '':
                    raise PathNotSpecified("Path not specified for save data. ")

                filename = directory + symbol.translate({ord(c): None for c in '!@#$/'}) + '.csv'
                if os.path.exists(filename):
                    # for existed file, first search for the last timestamp and then append OHLCV after that
                    with open(filename, 'rb') as file:
                        file.seek(-2, os.SEEK_END)        # Jump to the second last byte
                        while file.read(1) != b"\n":      # Until EOL is found...
                            file.seek(-2, os.SEEK_CUR)    # ...jump back the read byte plus one more
                        last = file.readline()
                        last_timestamp_in_file = int(last.split(b",")[0])

                    first_fetched_timestamp = self.last_OHLCV[symbol][0][0]

                    starting_row = (last_timestamp_in_file - first_fetched_timestamp) // (60 * 1000) + 1
                    if starting_row < 0:
                        raise OldDataNotContinuous("The last timestamp in the file is 1 min earlier than"
                                                   "the first timestamp in fetched data.")
                else:
                    # for newly created file, first write the header
                    starting_row = 0
                    with open(filename, 'a+', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(fieldnames)

                with open(filename, 'a+', newline='') as file:
                    writer = csv.writer(file)
                    for row in range(starting_row, len(self.last_OHLCV[symbol])):
                        writer.writerow(self.last_OHLCV[symbol][row])

            counter += 1
            time.sleep(self.exchange.rateLimit / 1000)

    def fetch_bidask(self, save=True):
        """
        Fetch current bidask for all tradable pairs
        Should call it every 1 min
        :return:
        """

        print("Fetching bidask from " + self.exchange_name + "...")
        if not self.load_markets():
            return

        fieldnames = ['timestamp', 'bid', 'ask', 'last']
        directory = self.path + self.exchange_name + '/' + self.directory['bidask'] + '/'

        for attempt in range(self.retry):
            try:
                data = self.exchange.fetch_tickers()
            except (ExchangeNotAvailable, ExchangeError, RequestTimeout) as exception:
                print('   ' + exception.__class__.__name__ + ', retry ' + str(attempt + 1) + '/' + str(self.retry))
                time.sleep(self.exchange.rateLimit / 1000)
                continue
            except DDoSProtection:
                print('   DDoSProtection error, cool down ' + str(self.cooldown) + "s...")
                time.sleep(self.cooldown)
                continue
            else:
                return True
        else:
            print('   Fail to load market')
            return False

        # to finish...

    def fetch_orderbook(self, save=True):
        """
        Fetch current orderbook data for all tradable pairs
        Should call it around 5-10 minutes

        """

        print("Fetching orderbook from " + self.exchange_name + "...")
        if not self.load_markets():
            return

        fieldnames = ['timestamp', 'datetime', 'asks', 'bids']
        directory = self.path + self.exchange_name + '/' + self.directory['orderbook'] + '/'

        counter = 1
        for symbol in self.exchange.markets:
            print('    ' + str(counter) + '/' + str(len(self.exchange.markets)) + ' ' + symbol)
            for attempt in range(self.retry):
                try:
                    data = self.exchange.fetchOrderBook(symbol, {'limit': 100})
                    self.last_orderbook[symbol] = [data['timestamp'], data['asks'], data['bids']]
                except (ExchangeNotAvailable, ExchangeError, RequestTimeout) as exception:
                    print('   ' + exception.__class__.__name__ + ', retry ' + str(attempt + 1) + '/' + str(self.retry))
                    time.sleep(self.exchange.rateLimit / 1000)
                    continue
                except DDoSProtection:
                    print('   DDoSProtection error, cool down ' + str(self.cooldown) + "s...")
                    time.sleep(self.cooldown)
                    continue
                else:
                    break
            else:
                print('   Fail to load orderbook ' + symbol)
                continue

            if save:
                if self.path == '':
                    raise PathNotSpecified("Path not specified for save data. ")

                to_write = [data['timestamp'], base64.b64encode(json.dumps(data['asks']).encode()).decode(),
                            base64.b64encode(json.dumps(data['bids']).encode()).decode()]
                # decode with: decode_strings = json.loads(base64.b64decode(encoded_string.encode()).decode())

                filename = directory + symbol.translate({ord(c): None for c in '!@#$/'}) + '.csv'

                if os.path.exists(filename):
                    with open(filename, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(to_write)
                else:
                    with open(filename, 'a+', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(fieldnames)
                        writer.writerow(to_write)

            counter += 1
            time.sleep(self.exchange.rateLimit / 1000)