"""
The backtest defines a class where exchange, algorithm is put in, and the back-test platform
will execute the algorithm against a given exchange, from start_timestamp to end_timestamp.
It saves necessary data to eventually plot graphs and calculate analyzed statistics.
"""

from backtest.BackExchange import BackExchange


class BackTestBase(object):
    def __init___(self, algorithm, exchange: BackExchange):
        pass
