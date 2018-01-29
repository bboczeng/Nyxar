# use a dict/list to maintain the position for every tradable assets
# use two lists to store history order and open order
# suggest create a class for order
# open order structure:
# timestamp (when placing it) | pair | order type: makret/limit | a bool for buy/sell | number | filled percentage
# history order structure
# timestamp (when filled) | pair | a bool for buy/sell | number


# here is what happens when a new timestamp is being processed:
# exchange check if there are open orders remaining
#   - If there are, check if orders can be filled or not, then update the position
# exchange sends the latest quote to the trading algo
# exchange takes request (place order / cancel order / history order) from the trading algo, then process it

# not sure about the time ordering here. but i think one should place order at current tick and process it at the
# next tick? or order is always processed within the same price in the same tick


# How to check if orders can be filled? (For OHLCV data)
# Market order:
# 1. Set the price to be this tick's close price (should be flexible to tune this. for example, use high for buy or
#    low to sell)
# 2. Slippage model. Here we first implement a fixed basispoint model. 0.05% fee for all trading, i.e., additional 
#    0.05% for buy, less 0.05% for sell. 
# 3. Check if there are enough quote currency based on the price. If not, (i never use market order. don't know if 
#    we should reject the order, or fill as much as possible)
# 4. If the order is only paritially filled, update the filled percentage and leave it in the open order for next cycle


# more to come
# exchange should be able to accept (optional) bid/ask, along with OHLCV. the slippage model should be able to run based
# on it. i think slippage is particularly important in cryptocurrency, due to the lack of liquidity and large bid-ask 
# spread for altcoins