from backtest.Errors import NotSupported, InsufficientFunds, InvalidOrder, OrderNotFound, SlippageModelError

from core.Quote import Quotes, QuoteFields
from core.Timer import Timer
from backtest.Order import OrderSide, OrderType, OrderStatus, Order, OrderBook, OrderQueue, Transaction
from backtest.Slippage import SlippageBase

from enum import Enum
from typing import List, Set, Tuple
from itertools import chain

from networkx.exception import NetworkXNoPath
import networkx as nx
import math


_TOLERANCE = 1e-9
_PREC = 8

class PriceType(Enum):
    Open = QuoteFields.Open
    High = QuoteFields.High
    Low = QuoteFields.Low
    Close = QuoteFields.Close


class BackExchange(object):
    def __init__(self, *, timer: Timer, quotes: Quotes,
                 buy_price: PriceType=PriceType.Open, sell_price: PriceType=PriceType.Open,
                 fee_rate: float=0.05, slippage_model: SlippageBase=SlippageBase()):
        assert isinstance(quotes, Quotes), "quotes has to be Quotes class"
        assert isinstance(buy_price, PriceType), "buy_price has to be PriceType class"
        assert isinstance(sell_price, PriceType), "sell_price has to be PriceType class"

        self._quotes = quotes
        self._timer = timer

        self._symbols, self._assets = self.__current_supported()

        self._total_balance = {}
        self._available_balance = {}
        for asset in self._assets:
            self._total_balance[asset] = 0
            self._available_balance[asset] = 0
        self._deposit_history = []

        self._submitted_orders = OrderQueue()
        self._open_orders = OrderBook()
        self._closed_orders = OrderBook()

        self._buy_price = buy_price
        self._sell_price = sell_price
        self._fee_rate = fee_rate
        self._slippage_model = slippage_model

        self._last_processed_timestamp = -1

    @property
    def __time(self):
        return self._timer.time

    def __frozen_balance(self, asset: str):
        return self._total_balance[asset] - self._available_balance[asset]

    def __get_price(self, symbol: str, price_type: PriceType) -> float:
        return self._quotes.get_quote(symbol).get_value(self.__time, price_type.value)

    def __get_volume(self, symbol: str) -> float:
        return self._quotes.get_quote(symbol).volume(self.__time)

    def __current_supported(self) -> Tuple[set, set]:
        supported_symbols, supported_assets = set(), set()
        for symbol in self._quotes:
            try:
                self.__get_volume(symbol)
                supported_symbols.add(symbol)
                supported_assets |= {self._quotes.get_quote(symbol).quote_name, self._quotes.get_quote(symbol).base_name}
            except KeyError:
                continue
        return supported_symbols, supported_assets

    def balance_in(self, target: str) -> float:
        G = nx.DiGraph()

        for symbol in self._symbols:
            quote_name = self._quotes.get_quote(symbol).quote_name
            base_name = self._quotes.get_quote(symbol).base_name
            G.add_edge(quote_name, base_name, weight=-math.log(self.__get_price(symbol, self._sell_price)))
            G.add_edge(base_name, quote_name, weight=math.log(self.__get_price(symbol, self._buy_price)))

        balance = 0
        for asset in self._total_balance:
            if self._total_balance[asset]:
                if asset == target:
                    balance += self._total_balance[asset]
                    continue
                try:
                    weight = nx.shortest_path_length(G, asset, target, "weight")
                except NetworkXNoPath:
                    raise Exception("Not possible to convert all assets to the target asset. ")
                balance += math.exp(-weight) * self._total_balance[asset]

        return balance

    def fetch_timestamp(self) -> int:
        """
        Returns:
             Current time of exchange in millisecond.
        """
        return self.__time

    def fetch_markets(self) -> Tuple[set, set]:
        """
        Returns:
             (Currently supported assets, Currently supported trading pairs) in sets
        """
        return self._assets.copy(), self._symbols.copy()

    def deposit(self, asset: str, amount: float) -> float:
        """
        Returns:
            The amount of successfully deposited asset.
        """
        if amount <= 0:
            return 0
        if asset in self._assets:
            self._total_balance[asset] += amount
            self._available_balance[asset] += amount
            self._deposit_history.append({'timestamp': self.__time, 'asset': asset, 'amount': round(amount, _PREC)})
            return amount
        else:
            raise NotSupported

    def withdraw(self, asset: str, amount: float) -> float:
        """
        Returns:
            The amount of successfully withdrawn asset.
        """
        if amount <= 0:
            return 0
        if asset in self._assets:
            if self._available_balance[asset] < amount:
                amount = self._available_balance[asset]
            self._total_balance[asset] -= amount
            self._available_balance[asset] -= amount
            self._deposit_history.append({'timestamp': self.__time, 'asset': asset, 'amount': round(-amount, _PREC)})
            return -amount
        else:
            raise NotSupported

    def fetch_deposit_history(self) -> list:
        """
        Returns:
             List of form: [{'timestamp': xxx, 'asset': xxx, 'amount':+/-xxx}, ...]
        """
        return self._deposit_history.copy()

    def fetch_balance(self) -> dict:
        """
        Returns:
            Dictionary of form: {symbol: {'total': xxx, 'free': xxx, 'used': xxx}, ...}
        """
        balance = {}
        for asset in self._assets:
            balance[asset] = {'total': round(self._total_balance[asset], _PREC),
                              'free': round(self._available_balance[asset], _PREC),
                              'used': round(self.__frozen_balance(asset), _PREC)}
        return balance

    def fetch_ticker(self, symbol: str='') -> dict:
        """
        Return the OHLCV data of the current timestamp for given symbol. If symbol not specified, return all supported
        symbols.

        Args:
            symbol: The ticker of symbol to be returned. If '', return that of all symbols. Defaults to ''.

        Returns:
            If symbol is specified, return the dictionary of form:
            {'open': xxx, 'high': xxx, 'low': xxx, 'close': xxx, 'volume': xxx}.
            If symbol is not specified, return the dictionary of form::
            {symbol: {'open': xxx, 'high': xxx, 'low': xxx, 'close': xxx, 'volume': xxx}, ...}.
        """
        if symbol == '':
            quotes = {}
            for symbol in self._symbols:
                quotes[symbol] = self.fetch_ticker(symbol)
            return quotes
        elif symbol not in self._symbols:
            raise NotSupported
        else:
            return self._quotes.get_quote(symbol).ohlcv(self.__time)

    def __execute_buy(self, order: Order, price: float, amount: float) -> bool:
        """
        This function does not check anything. It assumes in order balance has already been deducted from the available
        balance.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.side is OrderSide.Buy
        is_filled = order.execute_transaction(
            order.generate_transaction(amount=amount, price=price, timestamp=self.__time))

        quote_name = order.quote_name
        base_name = order.base_name
        fee = self._fee_rate / 100.0 * amount

        self._total_balance[quote_name] += amount - fee
        self._available_balance[quote_name] += amount - fee
        self._total_balance[base_name] -= price * amount
        # self._available_balance[base_name] -= price * amount
        # (Stop)Limit buy order may be filled with lower price, in which case the in order price needs to be compensated
        if order.type is not OrderType.Market:
            self._available_balance[base_name] += (order.price - price) * amount
        order.pay_fee(quote_name, fee)

        return is_filled

    def __execute_sell(self, order: Order, price: float, amount: float) -> bool:
        """
        This function does not check anything. It assumes in order balance has already been deducted from the available
        balance.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.side is OrderSide.Sell
        is_filled = order.execute_transaction(
            order.generate_transaction(amount=amount, price=price, timestamp=self.__time))

        quote_name = order.quote_name
        base_name = order.base_name
        fee = self._fee_rate / 100.0 * price * amount

        self._total_balance[quote_name] -= amount
        # self._available_balance[quote_name] -= amount
        self._total_balance[base_name] += price * amount - fee
        self._available_balance[base_name] += price * amount - fee
        order.pay_fee(base_name, fee)

        return is_filled

    def __execute_market_order(self, order: Order) -> bool:
        """
        This function does not check if the order is invalid / does not raise InvalidOrder exceptions. It only checks
        the validity of the slippage model and if the balance is sufficient.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.type is OrderType.Market and order.remaining == order.amount
        assert order.status is not OrderStatus.Cancelled

        price, amount = self._slippage_model.generate_tx(price=self.__get_price(order.symbol,
                                                               self._buy_price if order.side is OrderSide.Buy
                                                               else self._sell_price),
                                                         amount=order.remaining,
                                                         side=order.side,
                                                         order_type=order.type,
                                                         ticker=self.fetch_ticker(order.symbol),
                                                         timestamp=self.__time)

        if price < 0 or amount != order.remaining:
            raise SlippageModelError

        if order.side is OrderSide.Buy:
            base_name = order.base_name
            if price * amount > self._available_balance[base_name]:
                raise InsufficientFunds
            # self.__execute_buy assumes in order balance has already been deducted
            self._available_balance[base_name] -= amount * price
            return self.__execute_buy(order, price, amount)
        elif order.side is OrderSide.Sell:
            quote_name = order.quote_name
            if order.remaining > self._available_balance[quote_name]:
                raise InsufficientFunds
            # self.__execute_sell assumes in order balance has already been deducted
            self._available_balance[quote_name] -= amount
            return self.__execute_sell(order, price, amount)

    def __accept_market_order(self, order: Order):
        assert order.type is OrderType.Market
        if order.symbol not in self._symbols:
            # still need this, as a symbol may be delisted at this timestamp
            raise InvalidOrder
        else:
            # market order is never "open". if accepted, it is executed immediately
            self.__execute_market_order(order)
            assert order.status is OrderStatus.Filled
            self._closed_orders.insert_order(order)
            print('[BackExchange] Market order {:s} accepted and executed. '.format(str(order.id)))

    def __execute_limit_order(self, order: Order):
        """
        This function does not check if the order is invalid / does not raise InvalidOrder exceptions. It does not check
        if the balance is sufficient neither. It only checks the validity of the slippage.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert (order.type is OrderType.Limit) or (
                (order.type is OrderType.StopLimit) and (order.status is OrderStatus.Open))
        assert order.status is not OrderStatus.Cancelled

        is_filled = False
        price, amount = self._slippage_model.generate_tx(price=self.__get_price(order.symbol,
                                                               self._buy_price if order.side is OrderSide.Buy
                                                               else self._sell_price),
                                                         amount=order.remaining,
                                                         side=order.side,
                                                         order_type=order.type,
                                                         ticker=self.fetch_ticker(order.symbol),
                                                         timestamp=self.__time)

        if price < 0 or amount > order.remaining:
            raise SlippageModelError

        if order.side is OrderSide.Buy and price <= order.price:
            is_filled = self.__execute_buy(order, price, amount)

            if order.status is OrderStatus.Filled:
                print('[BackExchange] {:s}Limit buy order {:s} filled. '
                      .format('' if order.type is OrderType.Limit else 'Stop ', str(order.id)))
            else:
                print('[BackExchange] {:s}Limit buy order {:s} partially filled to {:2}%. '
                      .format('' if order.type is OrderType.Limit else 'Stop ', str(order.id), order.filled_percentage))
        elif order.side is OrderSide.Sell and price >= order.price:
            # Limit sell order never executes above the order price, even if there is a buy order with higher price
            is_filled = self.__execute_sell(order, order.price, amount)

            if order.status is OrderStatus.Filled:
                print('[BackExchange] {:s}Limit sell order {:s} filled. '
                      .format('' if order.type is OrderType.Limit else 'Stop ', str(order.id)))
            else:
                print('[BackExchange] {:s}Limit sell order {:s} partially filled to {:2}%. '
                      .format('' if order.type is OrderType.Limit else 'Stop ', str(order.id), order.filled_percentage))

        return is_filled

    def __accept_limit_order(self, order: Order):
        assert order.type is OrderType.Limit or order.type is OrderType.StopLimit
        if order.symbol not in self._symbols:
            raise InvalidOrder
        elif order.status is OrderStatus.Cancelled:
            self._closed_orders.insert_order(order)
        else:
            if order.side is OrderSide.Buy:
                base_name = order.base_name
                if order.amount * order.price > self._available_balance[base_name]:
                    raise InsufficientFunds
                self._available_balance[base_name] -= order.amount * order.price
            if order.side is OrderSide.Sell:
                quote_name = order.quote_name
                if order.amount > self._available_balance[quote_name]:
                    raise InsufficientFunds
                self._available_balance[quote_name] -= order.amount

            if order.type is OrderType.Limit:
                order.open()
                self._open_orders.insert_order(order)
                print('[BackExchange] Limit order {:s} accepted. '.format(str(order.id)))
            elif order.type is OrderType.StopLimit:
                order.accept()
                self._open_orders.insert_order(order)
                print('[BackExchange] Stop Limit order {:s} accepted. '.format(str(order.id)))

    def __open_stop_limit_order(self, order: Order) -> bool:
        assert order.type is OrderType.StopLimit
        if order.side is OrderSide.Buy and self.__get_price(order.symbol, self._buy_price) >= order.stop_price:
            order.open()
            print('[BackExchange] Stop Limit buy order {:s} opened. '.format(str(order.id)))
            return True
        elif order.side is OrderSide.Sell and self.__get_price(order.symbol, self._sell_price) <= order.stop_price:
            order.open()
            print('[BackExchange] Stop Limit sell order {:s} opened. '.format(str(order.id)))
            return True
        return False

    def create_order(self, *, symbol: str, side: OrderSide, order_type: OrderType, amount: float, price: float=0,
                     stop_price: float=0):
        if symbol not in self._symbols:
            # even if the symbol is supported in the next timestamp, in principle you shouldn't be able to know it
            # without first fetching a ticker
            raise InvalidOrder

        order_id = self._submitted_orders.add_new_order(timestamp=self.__time,
                                                        order_type=order_type,
                                                        side=side,
                                                        symbol=symbol,
                                                        amount=amount,
                                                        price=price,
                                                        stop_price=stop_price)
        return self.fetch_submitted_order(order_id)

    def create_market_buy_order(self, *, symbol: str, amount: float):
        return self.create_order(symbol=symbol, side=OrderSide.Buy, order_type=OrderType.Market, amount=amount)

    def create_market_sell_order(self, *, symbol: str, amount: float):
        return self.create_order(symbol=symbol, side=OrderSide.Sell, order_type=OrderType.Market, amount=amount)

    def create_limit_buy_order(self, *, symbol: str, amount: float, price: float):
        return self.create_order(symbol=symbol, side=OrderSide.Buy, order_type=OrderType.Limit, amount=amount,
                                 price=price)

    def create_limit_sell_order(self, *, symbol: str, amount: float, price: float):
        return self.create_order(symbol=symbol, side=OrderSide.Sell, order_type=OrderType.Limit, amount=amount,
                                 price=price)

    def create_stop_limit_buy_order(self, *, symbol, amount, price, stop_price):
        return self.create_order(symbol=symbol, side=OrderSide.Buy, order_type=OrderType.StopLimit, amount=amount,
                                 price=price, stop_price=stop_price)

    def create_stop_limit_sell_order(self, *, symbol, amount, price, stop_price):
        return self.create_order(symbol=symbol, side=OrderSide.Sell, order_type=OrderType.StopLimit, amount=amount,
                                 price=price, stop_price=stop_price)

    def cancel_submitted_order(self, order_id):
        """
        Submitted order is like a cache. If submitted order is cancelled, it is as if the request if not sent to the
        exchange. Therefore, it does not leave any history.
        """
        self._submitted_orders[order_id].cancel()

    def cancel_open_order(self, order_id: str):
        order = self._open_orders[order_id]
        # order status
        order.cancel()
        # order book management
        self._open_orders.remove_order(order)
        self._closed_orders.insert_order(order)
        # in order balance refund
        if order.side is OrderSide.Buy:
            self._available_balance[order.base_name] += order.remaining * order.price
        elif order.side is OrderSide.Sell:
            self._available_balance[order.quote_name] += order.remaining
        print("[BackExchange] Open order {:s} cancelled. ".format(order_id))

    def fetch_submitted_order(self, order_id: str) -> dict:
        return self._submitted_orders[order_id].info

    def fetch_submitted_orders(self, limit: int=0) -> list:
        return self._submitted_orders.get_orders(limit, id_only=False)

    def fetch_order(self, order_id: str) -> dict:
        try:
            order = self._open_orders[order_id]
        except OrderNotFound:
            order = self._closed_orders[order_id]

        return order.info

    def fetch_open_orders(self, *, symbol: str='', limit: int=0):
        return self._open_orders.get_orders(symbol, limit, id_only=False)

    def fetch_closed_orders(self, *, symbol: str, limit: int=0):
        return self._closed_orders.get_orders(symbol, limit, id_only=False)

    def balance_consistency_check(self):
        # check asset list
        assert self._assets == set(self._total_balance.keys()) == set(self._available_balance.keys())

        in_order_balance, total_balance = {}, {}
        for asset in self._assets:
            in_order_balance[asset] = 0

        # check in order balance
        for order in self._open_orders:
            if order.side is OrderSide.Buy:
                in_order_balance[order.base_name] += order.remaining * order.price
            elif order.side is OrderSide.Sell:
                in_order_balance[order.quote_name] += order.remaining
        for asset in in_order_balance:
            assert abs(self.__frozen_balance(asset) - in_order_balance[asset]) < _TOLERANCE

        # check total balance
        # note that history transactions may include already delisted assets
        for deposit in self._deposit_history:
            if deposit['asset'] not in total_balance:
                total_balance[deposit['asset']] = 0
            total_balance[deposit['asset']] += deposit['amount']
        for order in chain(self._closed_orders, self._open_orders):
            base_name = order.base_name
            quote_name = order.quote_name
            if base_name not in total_balance:
                total_balance[base_name] = 0
            if quote_name not in total_balance:
                total_balance[quote_name] = 0

            if order.side is OrderSide.Buy:
                for tx in order.transactions:
                    total_balance[base_name] -= tx.amount * tx.price
                    total_balance[quote_name] += tx.amount
            elif order.side is OrderSide.Sell:
                for tx in order.transactions:
                    total_balance[base_name] += tx.amount * tx.price
                    total_balance[quote_name] -= tx.amount
            fee = order.fee
            for asset in fee:
                total_balance[asset] -= fee[asset]

        for asset in total_balance:
            #print(asset, self._total_balance[asset], total_balance[asset])
            assert abs(self._total_balance[asset] - total_balance[asset]) < _TOLERANCE

    def process(self):
        print('[BackExchange] Current timestamp: {}'.format(self.__time))
        if self.__time == self._last_processed_timestamp:
            raise Exception("Same timestamp shouldn't be processed more than once. ")

        # newly list and delist assets
        symbols, assets = self.__current_supported()
        # newly list
        for asset in assets - self._assets:
            print('[BackExchange] Newly list: {}'.format(asset))
            self._total_balance[asset] = 0
            self._available_balance[asset] = 0
        # delist
        for asset in self._assets - assets:
            print('[BackExchange] Delist: {}'.format(asset))
            for order_id in self._open_orders.get_orders():
                order = self._open_orders[order_id]
                if order.base_name == asset or order.quote_name == asset:
                    self.cancel_open_order(order_id)
            assert self.__frozen_balance(asset) == 0
            self.withdraw(asset, self._total_balance[asset])
            del self._total_balance[asset]
            del self._available_balance[asset]
        self._symbols, self._assets = symbols, assets


        # resolve orders
        # resolve submitted order
        while self._submitted_orders:
            order = self._submitted_orders.pop_order()
            if order.status is OrderStatus.Cancelled:
                continue
            if order.type is OrderType.Market:
                self.__accept_market_order(order)
            elif order.type is OrderType.Limit or order.type is OrderType.StopLimit:
                self.__accept_limit_order(order)

        # resolve open orders
        for order_id in self._open_orders.get_orders():
            order = self._open_orders[order_id]
            if order.type is OrderType.StopLimit and order.status is OrderStatus.Accepted:
                self.__open_stop_limit_order(order)
            if order.status is OrderStatus.Open and self.__execute_limit_order(order):
                self._open_orders.remove_order(order)
                self._closed_orders.insert_order(order)

        self._last_processed_timestamp = self.__time

        # check if balance is consistent with order books
        self.balance_consistency_check()


