.. _rst_backexchange:

BackExchange
=============

Overview
*************
BackExchange is a simulative exchange for backtesting your trading algorithms. Its API mimics that in `ccxt <https://github.com/ccxt/ccxt>`_ library, which supports live trading on more than 90 mainstrem cryptocurrency exchanges. The intention is to make minimal difference between algorithms in the backtest and in the live trading.

The essential data taken by :class:`BackExchange` are timestamped OHLCV tickers, which are fed through :class:`Quotes` when it is first intialized. Its clock is controlled by the :class:`Timer`. At each time bar, :class:`BackExchange` takes and processes orders just like a real exchange.


Still, there are some features that are dedicated to backtesting, which we will go through in the following. 


Features
**************

Order Queue
---------------
In event based backtesting, orders placed at this time bar are processed at next, while in live trading orders are processed instantly. Therefore, all orders submitted to :class:`BackExchange` are first cached in an order queue, and wait to be processed at the beginning of the next time bar. As its name suggests, queued orders are processed in a first-in-first-out manner. Submitted orders can be cancelled through :meth:`BackExchange.cancel_submitted_order`. Cancelled submitted orders will not appear in order history, as if order requests are never sent to the exchange. 


List and Delist
----------------
A common pitfall in backtesting strategies is `survivor bias <https://www.investopedia.com/terms/s/survivorshipbias.asp>`_, which can happen when assets are delisted from an exchange but are not included in the testing data. :class:`BackExchange` supports listing and delisting assets or trading pairs by simply checking existing trading pairs at the current time bar. All currently supported trading pairs and assets can be queried through :meth:`BackExchange.fetch_markets`. 

If a previously existed trading pair doesn't exist any more, all open orders under it will be forcely closed. If a previously existed asset doesn't appear in any trading pair, it is considered as delisted. The remaining balance will be forcely withdrawn. Withdrawal history can be queried through :meth:`BackExchange.fetch_deposit_history`.


Slippage
---------------
In real life trading, orders are usually not filled at the ticker price for various reasons. This process, called `slippage <https://en.wikipedia.org/wiki/Slippage_(finance)>`_, is taken care in :class:`BackExchange` in the following aspects:

* Orders placed at this time bar is always processed at next to simulate time delay.  

* Buy and sell orders can be filled at different type of prices (for example, buy orders are filled at high price and sell orders are filled at low price in the ticker). These can be set when :class:`BackExchange` is first initialized, or changed any time through c:attr:`BackExchange.buy_price` and :attr:`BackExchange.sell_price`. 

* Transaction fee as fixed rate slippage. Buy orders are always filled `0.01x%` higher than the ticker price and sell orders are always filled `0.01x%` lower than the ticker price. `x` is the transaction fee rate in the unit of basis point. It can be set when :class:`BackExchange` is first initialized, or changed any time through :attr:`BackExchange.fee_rate`. 

* Slippage model. Given ticker price and any custom data as input, the slippage model determines the amount and the price to be filled for a given order. It can be set when :class:`BackExchange` is first initialized, or changed any time through :attr:`BackExchange.slippage_model`. Nyxar provides several predefined slippage models, such as spread slippage and volume slippage. Nyxar also supports user defined slippage model. For more details, see :ref:`rst_slippage`.


API Reference
****************

.. py:class:: BackExchange(timer, quotes[, buy_price=PriceType.Open, sell_price=PriceType.Open, fee_rate=0.05, slippage_model=SlippageBase())

   BackExchange used for backtesting. 

   * timer: :rst:dir:`timer` class used to control the clock of BackExchange. 

   * quotes: :rst:dir:`quotes` class contains timestamped OHLCV tickers. 

   * buy_price: The price type that all buy orders are filled at. Defaults to PriceType.Open. 

   * sell_price: The price type that all sell orders are filled at. Defaults to PriceType.Open. 

   * fee_rate: Fee taken by the exchange for all orders in the unit of base point. Defaults to 0.05. 

   * slippage_model: :rst:dir:`SlippageBase` class used to compute order slippage. Defaults to SlippageBase where there is no slippage.

   **Attributes:**

   .. attribute:: buy_price

   .. attribute:: sell_price

   .. attribute:: fee_rate

      The fee rate imposed by the exchange on all orders. The unit is base point. 

   .. attribute:: slippage_model

      The fee rate imposed by the exchange on all orders. The unit is base point. 


   **User methods:**

   The following are user methods that resemble public APIs that are provided by an exchange. 

      .. method:: fetch_timestamp()

         Return the current timestamp of BackExchange in millisecond. 

      .. method:: fetch_markets()

         Return a tuple of dictionaries contain currently supported asset names and trading pair symbols. 

      .. method:: fetch_ticker([symbol=''])

         Return the OHLCV data of the current time bar for given symbol. If symbol not specified, return tickers for all supported symbols. 

         If symbol is specified, returned dictionary is of form::

         {'open': xxx, 'high': xxx, 'low': xxx, 'close': xxx, 'volume': xxx}.
         
         If symbol is not specified, return the dictionary of form::
         
         {symbol: {'open': xxx, 'high': xxx, 'low': xxx, 'close': xxx, 'volume': xxx}, ...}.

   The following are user methods that resemble private APIs that are provided by an exchange. 

      .. method:: deposit(asset, amount)

         Deposit amount of asset into the balance. Return the successfully deposited amount. Any negative amount will be cast to zero. Raise NotSupported if the asset is not supported at this timestamp. 

      .. method:: withdraw(asset, amount)

         Withdraw amount of asset into the balance. Return the successfully withdraw amount (negative). Any negative amount will be cast to zero. Raise NotSupported if the asset is not supported at this timestamp. 

      .. method:: fetch_balance()

         Return all current balances in a dictionary of form: {asset: {'total': xxx, 'free': xxx, 'used': xxx}, ...}. 

      .. method:: fetch_balance_in(target[, fee=False])

         Return the total balance in the target asset, based on the ticker at current time bar. The method will automatically finds the most profitable way to convert an asset to the target asset if there are more than one ways. 

         If fee=True, the converted balance is computed by taking transaction fee into account (fee rate is defined when BackExchange is first initialized). Defaults to False. 

      .. method:: fetch_deposit_history()

         Return a list of deposit and withdraw history, in the form [{'timestamp': xxx, 'asset': xxx, 'amount':+/-xxx}, ...]

      .. method:: create_market_buy_order(symbol, amount)
      .. method:: create_market_sell_order(symbol, amount)

         Create and submit a market buy/sell order for a given symbol and amount to the order queue. Return the info of placed order. 

      .. method:: create_limit_buy_order(symbol, amount, price)
      .. method:: create_limit_sell_order(symbol, amount, price)

         Create and submit a limit buy/sell order for a given symbol, amount and limit price to the order queue. Return the info of placed order. 

      .. method:: create_stop_limit_buy_order(symbol, amount, price, stop_price)
      .. method:: create_stop_limit_sell_order(symbol, amount, price, stop_price)

         Create and submit a limit buy/sell order for a given symbol, amount, limit price and stop price to the order queue. Return the info of placed order. 

      .. method:: cancel_submitted_order(order_id)

         Cacnel the submitted order with `order_id` in the order queue. 

      .. method:: cancel_open_order(order_id)

         Cancel the open order with order_id in the order queue. 

      .. method:: fetch_submitted_order(order_id)

         Return the order info of order in the order queue with order_id. 

      .. method:: fetch_submitted_orders([limit=0])

         Return at most recent limit orders with order infos in time order in a list. If limit=0, return all orders. 

      .. method:: fetch_order(order_id)

         Return the order info of order in the open order book or history order with order_id. 

      .. method:: fetch_open_orders([symbol='', limit=0])
      .. method:: fetch_close_orders(symbol, [, limit=0])

         Return the order info of at most recent limit orders under a trading symbol in the open order book in time order in a list. If symbol='', return orders with all symbols (only available for fetching open orders). If limit=0, return all orders. 






      