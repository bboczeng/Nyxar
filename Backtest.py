import core.Quote as q
from backtest.BackExchange import BackExchange
from Algo import TradingAlgo
from AlgoMovingAverage import MovingAverageTradingAlgo

file_path = '.../NewData/binance/test/'

one_minute = 60 * 1000

start_timestamp = 1517260800000 + one_minute * 10
end_timestamp = 1517266560000

ex = BackExchange(quotes=q.batch_quotes_csv_reader(file_path))
ex.deposit('ETH', 1000)

algo = TradingAlgo(ex)
algo.initialize()
"""
for t in range(start_timestamp, end_timestamp, one_minute):
    ex.process_timestamp(t)
    algo.execute()
"""
ex2 = BackExchange(quotes=q.batch_quotes_csv_reader(file_path))
ex2.deposit('ETH', 1000)

algo_ma = MovingAverageTradingAlgo(ex2)
# moving agerage set for 10 minute window size
algo_ma.initialize(10)

for t in range(start_timestamp, end_timestamp, one_minute):
    ex2.process_timestamp(t)
    algo_ma.execute()