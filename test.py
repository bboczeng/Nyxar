import core.quote as q
from backtest.backexchange import BackExchange
from Algo import TradingAlgo

file_path = '/Users/andrewshen/Dropbox (Personal)/CRAB/NewData/binance/test/'

start_timestamp = 1517260800000 + 60000 * 10
end_timestamp = 1517266560000

ex = BackExchange(quotes=q.batch_quotes_csv_reader(file_path))
ex.deposit('ETH', 1000)

algo = TradingAlgo(ex)
algo.initialize()

for t in range(start_timestamp, end_timestamp, 60 * 1000):
    ex.current_timestamp = t
    ex.process_timestamp()
    algo.execute()

#for order in ex.history_orders:
#    print(order.transactions)