.. _rst_backexchange:

BackExchange
=============

Overview
*************
:class:`BackExchange` is a simulative exchange for backtesting your trading algorithms. Its API mimics that in `ccxt <https://github.com/ccxt/ccxt>`_ library, which supports live trading on more than 90 mainstrem cryptocurrency exchanges. The intention is to make minimal difference between algorithms in the backtest and in the live trading.

The essential data taken by :class:`BackExchange` are timestamped OHLCV tickers, which are fed through :class:`Quotes` when it is first intialized. Its clock is controlled by the :class:`Timer`. At each time bar, :class:`BackExchange` takes and processes orders just like a real exchange.

.. note::

   * All tickers and balance are processed and returned with 8 decimal places. 

   * Order matching is in favor of buyers. For example, if there is a sell order placed at price `10.0` and a buy order placed at `10.5`, the order will be executed at `10.0`. 


Features
**************

.. _order-queue:

Order Queue
---------------
In event based backtesting, orders placed at this time bar are processed at next, while in live trading orders are processed instantly. Therefore, all orders submitted to :class:`BackExchange` are first cached in an order queue, and wait to be processed at the beginning of the next time bar. 

Order queue raises several complication:

* As its name suggests, queued orders are processed in a first-in-first-out manner. This may cause later submitted orders rejected due to insufficient funds. 

* Submitted orders can be cancelled through :meth:`BackExchange.cancel_submitted_order`. Cancelled submitted orders will not appear in closed order book, as if order requests are never sent to the exchange. 

* When an invalid order is submitted to the order queue, an exception may be raised at the moment when the order is submitted or the moment when the order is processed at the beginning of next time bar, depending on the time that the error can be detected. See `Exceptions`_ for more details. 

.. seealso::
         More about :ref:`rst_order`. 


List and Delist
----------------
A common pitfall in backtesting strategies is `survivor bias <https://www.investopedia.com/terms/s/survivorshipbias.asp>`_, which can happen when assets are delisted from an exchange but are not included in the testing data. :class:`BackExchange` supports listing and delisting assets or trading pairs by simply checking existing trading pairs at the current time bar. All currently supported trading pairs and assets can be queried through :meth:`BackExchange.fetch_markets`. 

If a previously existing trading pair doesn't exist any more, all open orders under it will be forcely closed. If a previously existing asset doesn't appear in any trading pair, it is considered as delisted. The remaining balance will be forcely withdrawn. Withdrawal history can be queried through :meth:`BackExchange.fetch_deposit_history`.


Slippage
---------------
In real life trading, orders are usually not filled at the ticker price for various reasons. This process, called `slippage <https://en.wikipedia.org/wiki/Slippage_(finance)>`_, is taken care in :class:`BackExchange` in the following aspects:

* Orders placed at this time bar is always processed at next to simulate time delay.  

* Buy and sell orders can be filled at different type of prices (for example, buy orders are filled at high price and sell orders are filled at low price in the ticker). These can be set when :class:`BackExchange` is first initialized, or changed any time through :attr:`BackExchange.buy_price` and :attr:`BackExchange.sell_price`. 

* Transaction fee as fixed rate slippage. Buy orders are always filled `0.01x%` higher than the ticker price and sell orders are always filled `0.01x%` lower than the ticker price. `x` is the transaction fee rate in the unit of basis point. It can be set when :class:`BackExchange` is first initialized, or changed any time through :attr:`BackExchange.fee_rate`. 

* Slippage model. Given ticker price and any custom data as input, the slippage model determines the amount and the price to be filled for a given order. It can be set when :class:`BackExchange` is first initialized, or changed any time through :attr:`BackExchange.slippage_model`. Nyxar provides several predefined slippage models, such as spread slippage and volume slippage. Nyxar also supports user defined slippage model. See :ref:`rst_slippage` for more details.


API Reference
****************

.. py:class:: BackExchange(timer, quotes[, buy_price=PriceType.Open, sell_price=PriceType.Open, fee_rate=0.05, slippage_model=SlippageBase())

   BackExchange used for backtesting. 

   * timer: :class:`Timer` class used to control the clock of BackExchange. 

   * quotes: :class:`Quotes` class contains timestamped OHLCV tickers. 

   * buy_price: Set :attr:`.buy_price`. Defaults to `'open'`. 

   * sell_price: Set :attr:`.sell_price`. Defaults to `'open'`. 

   * fee_rate: Set :attr:`.fee_rate`. Defaults to 0.05. 

   * slippage_model: Set :attr:`.slippage_model`. Defaults to :class:`SlippageBase`. 

   **Attributes:**

   .. attribute:: buy_price

      The price types that all buy orders are filled at. Its value can be of one the following four strings: `'open'`, `'high'`, `'low'`, `'close'`. 

   .. attribute:: sell_price

      The price types that all sell orders are filled at. Its value can be of one the following four strings: `'open'`, `'high'`, `'low'`, `'close'`. 

   .. attribute:: fee_rate

      The fee rate imposed by the exchange on all orders in the unit of basis point. Buy orders are always filled `0.01 * fee_rate%` higher than the ticker price and sell orders are always filled `0.01 * fee_rate%` lower than the ticker price. 

      In practice, the fee is taken by deducting quote asset for buy orders, and base asset for sell orders. In other words, you will always receive less asset than the amount appears in the order. 

   .. attribute:: slippage_model

      The slippage model to determine how an order should be filled. See :ref:`rst_slippage` for more details.


   **User methods:**

   The following are user methods that resemble public APIs provided by an exchange. 

      .. method:: fetch_timestamp()

         Return the current timestamp in millisecond. 

      .. method:: fetch_markets()

         Return a tuple of dictionaries contain currently supported asset names and trading pair symbols. 

      .. method:: fetch_ticker([symbol=''])

         Return the OHLCV tickers of the current time bar for the given `symbol`. If `symbol` not specified, return tickers for all supported symbols. 

         ::

            >>> ex.fetch_ticker(symbol='FOO/BAR')
            {'open': 1.2, 'high': 3.4, 'low': 5.6, 'close': 7.8, 'volume': 9.0}
            >>> ex.fetch_ticker()
            {'FOO': {'open': 1.2, 'high': 3.4, 'low': 5.6, 'close': 7.8, 'volume': 900.0}, 
             'BAR': {'open': 9.0, 'high': 7.8, 'low': 3.5, 'close': 4.6, 'volume': 120.2}, ...}.

   The following are user methods that resemble private APIs provided by an exchange. 

      .. method:: deposit(asset, amount)
      .. method:: withdraw(asset, amount)

         Deposit / Withdraw `amount` of `asset` into the balance. Any negative `amount` will be cast to zero. Return successfully deposited / withdrawn amount. 

      .. method:: fetch_balance()

         Return all current balances in a dictionary. 

         ::

            >>> ex.fetch_balance()
            {'FOO': {'total': 100.0, 'free': 99.5, 'used': 0.5}, 
             'BAR': {'total': 78.0, 'free': 78.0, 'used': 0}, ...}. 

      .. method:: fetch_balance_in(target[, fee=False])

         Return the total balance in the `target` asset, based on tickers at the current time bar. The method will automatically finds the most profitable way to convert an asset to `target` if there are more than one ways. A :exc:`NotSupported` exception will be raised if there exists an asset that is unable to convert to target. 

         If `fee=True`, the converted balance is computed by taking transaction fee into account. Defaults to `False`. 

      .. method:: fetch_deposit_history()

         Return a list of deposit and withdrawl history.

         ::

            >>> ex.fetch_deposit_history()
            [{'timestamp': 1517599560000, 'asset': 'FOO', 'amount': 100}, {'timestamp': 1517599620000, 'asset': 'FOO', 'amount': -5}]

      .. method:: create_market_buy_order(symbol, amount)
      .. method:: create_market_sell_order(symbol, amount)

         Create and submit a market buy/sell order under `symbol` of `amount` to the order queue. Return the info of placed order. 

         ::

            >>> ex.create_market_buy_order('FOO/BAR', 100)
            {'id': 693461813487499546, 
            'datetime': '2018-02-02 14:26:00', 
            'timestamp': 1517599560000, 
            'status': 'submitted', 
            'symbol': 'FOO/BAR', 
            'type': 'market', 
            'side': 'buy', 
            'price': 0, 
            'stop_price': 0, 
            'amount': 100, 
            'filled': 0, 
            'remaining': 100, 
            'transaction': [], 
            'fee': {}}

      .. method:: create_limit_buy_order(symbol, amount, price)
      .. method:: create_limit_sell_order(symbol, amount, price)

         Create and submit a limit buy/sell order under `symbol` of `amount` to the order queue. The limit price of the order is `price`. Return the info of placed order. 

      .. method:: create_stop_limit_buy_order(symbol, amount, price, stop_price)
      .. method:: create_stop_limit_sell_order(symbol, amount, price, stop_price)

         Create and submit a stop limit buy/sell order under `symbol` of `amount` to the order queue. The limit price of the order is `price`, and the stop limit price is `stop_price`. Return the info of placed order. 


      .. method:: cancel_submitted_order(order_id)

         Cacnel the submitted order in the order queue whose id is `order_id`. 

      .. method:: cancel_open_order(order_id)

         Cancel the open order in the open order book whose id is `order_id`.

      .. method:: fetch_submitted_order(order_id)

         Return :attr:`Order.info` of the submitted order in the order queue whose id is `order_id`.

      .. method:: fetch_submitted_orders([limit=500])

         Return :attr:`Order.info` of last `limit` submitted orders in the order queue. If `limit=0`, return info of all submitted orders. `limit` defaults to `500`. 

      .. method:: fetch_order(order_id)

         Return :attr:`Order.info` of the order whose id is `order_id` in the open order book or closed order book.

      .. method:: fetch_open_orders([symbol='', limit=500])

         Return :attr:`Order.info` of last `limit` open orders in the open order book. If `symbol` is specified, only orders under that trading symbols are returned. Otherwise all open orders will be returned. If `limit=0`, return info of all open orders. `limit` defaults to `500`. 

      .. method:: fetch_closed_orders(symbol[, limit=500])

         Return :attr:`Order.info` of last `limit` closed orders in the closed order book. Different from :meth:`.fetch_open_orders`, `symbol` must be specified. 

Exceptions
****************

.. exception:: NotSupported

   Raised when an unsupported asset or trading pair symbol is queried. 

.. exception:: InsufficientFunds

   Raised when there are no enough funds to place an order. This exception will only be raised at the beginning of a time bar when the order is being processed by the exchange. 

.. exception:: InvalidOrder

   Raised when an invalid order is submitted. For invalid orders with negaive amount or price, this exception will be raised immediately when orders are created. For invalid orders with non-existing trading pair symbol, this exception will be raised at the beginning of the next time bar. 

.. exception:: OrderNotFound

   Raised when a particular order is not found (usually queried through order id) in the order book. 

