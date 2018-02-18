import core.Quote as q
from core.Timer import Timer
from backtest.BackExchange import BackExchange
from backtest.Slippage import VolumeSlippage
from Algo import TradingAlgo
from AlgoMovingAverage import MovingAverageTradingAlgo

file_path = '.../NewData/binance/test/'

one_minute = 60 * 1000


timer = Timer(1517260800000 + one_minute * 10, 1517266560000, one_minute)


ex = BackExchange(timer=timer, quotes=q.batch_quotes_csv_reader(file_path), slippage_model=VolumeSlippage(0.1))
ex.deposit('ETH', 1000)

algo = TradingAlgo(ex)
algo.initialize()
while True:
    ex.process()
    algo.execute()
    if timer.next():
        break

timer2 = Timer(1517260800000 + one_minute * 10, 1517266560000, one_minute)


ex2 = BackExchange(timer=timer2, quotes=q.batch_quotes_csv_reader(file_path))
ex2.deposit('ETH', 1000)

algo_ma = MovingAverageTradingAlgo(ex2)
# moving agerage set for 10 minute window size
algo_ma.initialize(10)
while True:
    ex2.process()
    algo_ma.execute()
    if timer2.next():
        break

