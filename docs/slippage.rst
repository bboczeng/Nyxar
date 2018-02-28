.. _rst_slippage:


Slippage Model
================

Overview
*************
In real life trading, orders are usually not filled at the ticker price for various reasons. In order to make backtest results reliable, Nyxar takes slippage into account at various levels (see :ref:`be-slippage`). In particular, slippage models are responsible to simulate `market impact <https://en.wikipedia.org/wiki/Market_impact>`_ of the order. Nyxar has two builtin slippage models, and users can easily create their own more sophisticated slippage models. 

By default, :class:`BackExchange` doesn't use any slippage model. To set up slippage model, assign :attr:`BackExchange.slippage_model` to be an instance of slippage model class. 

::

	from Nyxar import VolumeSlippage, SpreadSlippage, SpreadVolumeSlippage
	ex.slippage_model = VolumeSlippage(tradable_rate=2.5)
	ex.slippage_model = SpreadSlippage(bidask=data, spread_rate=50)
	ex.slippage_model = SpreadVolumeSlippage(bidask=data, spread_rate=50, tradable_rate=2.5)


Orders will be automatically processed with the slippage model. 

Slippage Models
*****************

Volume Slippage
---------------------------
Volume slippage model uses the volume data provided by :class:`BackExchange`. At each time bar, at most `tradable_rate%` of total volume can be filled *per order*. The remaining amount of the order will be processed at next time bar. By default, `tradable_rate=2.5`. 

Volume slippage model is only applicable to limit or stop limit orders. Market orders will always be filled in full. Avoid placing large market orders with volume slippage model. 


Spread Slippage
---------------------------

Spread slippage model uses additional `bid-ask spread <https://en.wikipedia.org/wiki/Bid%E2%80%93ask_spread>`_ data provided by the user through :class:`BidAsks`. All buy/sell orders are filled at price additional `spread_rate% * spread` higher/lower. By default, `spread_rate=50`. 

Spread slippage model is applicable to all order types. 


Volume-Spread Slippage
---------------------------

Volume-spread slippage is simply a combination of the volume slippage model and spread slippage model. 


Custom Slippage
---------------------------

Users can define their own slippage model by defining a child class of :class:`SlippageBase`. 

.. py:class:: SlippageBase(*args, **kwargs)

		.. method:: __init__(*args, **kwargs)

			User should overwrite :meth:`.__init__` method doing necessary data feeding or initialization. 

		.. method:: generate_tx(price, amount, order_type, order_side, symbol, ticker, timestamp)

			* `price`: The original tentative ticker price for the order to fill at. 

			* `amount`: The remaining amount in the order to fill. 

			* `order_type`: Order type as a :class:`OrderType` enumeration class.  

			* `order_side`: Order side as a :class:`OrderSide` enumeration class.  

			* `symbol`: Trading pair symbol of the order. 

			This method should return a tuple `(tx_price, tx_amount)` which represents a tentative transaction. In the transaction, `tx_amount` is filled at price `tx_price`. :class:`BackExchange` will check if the tentative transaction will actually happen (for example, if `tx_price` is in the range of the limit price of the limit order), and will generate the transaction for you. 

			However, it is user's responsibility to make sure `(tx_price, tx_amount)` is valid. For example, `tx_amount == amount` for market orders. Otherwise :exc:`SlippageModelError` will be raised by :class:`BackExchange`. 

