BackExchange
=============

Overview
*************
BackExchange is a simulative exchange for backtesting your trading algorithms. Its API mimics that in ccxt_ library, which supports live trading on more than 90 mainstrem cryptocurrency exchanges. The intention is to make minimal difference between algorithms in the backtest and in the live trading.

.. _ccxt: https://github.com/ccxt/ccxt

The essential data taken by BackExchange are timestamped OHLCV tickers, which are fed through :rst:dir:`quotes` class when it is first intialized. Its clock is controlled by the :rst:dir:`timer` class. At each time bar, it takes and processes orders just like a real exchange.

Still, there are some features that are dedicated to backtesting, which we will go through in the following. 

Order Queue
---------------
A fundamental difference between live trading and event based backtesting is that order placed at this time bar is processed at next, while in live trading the order is processed instantly. Therefore, all orders submitted to BackExchange are first cached in an order queue, and wait to be processed at the beginning of the next time bar. 


Slippage
---------------
In real life trading, orders are usually not filled at the ticker price. This process, called slippage, is taken care in BackExchange in the following aspects:

* Fixed rate slippage: Transaction fee. 

* Buy and Sell orders can be filled at different prices. 

* Slippage model. 




This is the reference page

.. py:function:: enumerate(sequence[, start=0])

   Return an iterator that yields tuples of an index and an item of the
   *sequence*. (And so on.)