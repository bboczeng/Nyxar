from core.Ticker import Quotes
from core.Timer import Timer
from backtest.BackExchange import BackExchange
from backtest.Slippage import VolumeSlippage
from algorithm.simpleAlgos import SimpleTradingAlgo, MovingAverageTradingAlgo

file_path = '../../data/binance/'
one_minute = 60 * 1000

timer = Timer(1517599560000, 1517604900000, one_minute)

quotes = Quotes()
quotes.add_tickers_csv(file_path)

ex = BackExchange(timer=timer, quotes=quotes, slippage_model=VolumeSlippage(0.1))
ex.deposit('ETH', 1000)

algo = SimpleTradingAlgo(ex)
algo.initialize()
while True:
    ex._process()
    algo.execute()
    if timer.next():
        break

timer2 = Timer(1517599560000, 1517604900000, one_minute)

quotes2 = Quotes()
quotes2.add_tickers_csv(file_path)

ex2 = BackExchange(timer=timer2, quotes=quotes2)
ex2.deposit('ETH', 1000)

algo_ma = MovingAverageTradingAlgo(ex2, 10)
# moving average set for 10 minute window size
algo_ma.initialize()
while True:
    ex2._process()
    algo_ma.execute()
    if timer2.next():
        break
