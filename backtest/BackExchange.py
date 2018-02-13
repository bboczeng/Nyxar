from backtest.errors import NotSupported, InsufficientFunds, InvalidOrder, OrderNotFound, SlippageModelError

from core.quote import Quotes, QuoteFields
from backtest.order import OrderSide, OrderType, OrderStatus, Order, OrderBook, OrderQueue, Transaction
from backtest.slippage import slippage_base

from enum import Enum
from typing import List, Set, Tuple


# to do: restrict returned order number
#        stop limit / stop loss order
#        asset rebrand
#        newly listed asset / delisted asset

class PriceType(Enum):
    Open = QuoteFields.Open
    High = QuoteFields.High
    Low = QuoteFields.Low
    Close = QuoteFields.Close


class BackExchange(object):
    def __init__(self, *, quotes: Quotes, buy_price: PriceType=PriceType.Open, sell_price: PriceType=PriceType.Open,
                 fee_rate=0.05, slippage_model=slippage_base, supplement_data=None):
        assert isinstance(quotes, Quotes), "quotes has to be Quotes class"
        assert isinstance(buy_price, PriceType), "quotes has to be Quotes class"
        assert isinstance(sell_price, PriceType), "quotes has to be Quotes class"

        self.quotes = quotes
        self.symbols = self.quotes.get_symbols()
        self.assets = self.quotes.get_assets()

        self.total_balance = {}
        self.available_balance = {}
        for asset in self.assets:
            self.total_balance[asset] = 0
            self.available_balance[asset] = 0

        self.submitted_order = OrderQueue()
        self.open_orders = OrderBook()
        self.closed_orders = OrderBook()

        self.current_timestamp = 0

        self.buy_price = buy_price
        self.sell_price = sell_price
        self.fee_rate = fee_rate
        self.slippage_model = slippage_model
        self.supplement_data = None

    def __frozen_balance(self, asset: str) -> float:
        return self.total_balance[asset] - self.available_balance[asset]

    def __get_price(self, symbol: str, price_type: PriceType) -> float:
        return self.quotes.get_quote(symbol).get_value(self.current_timestamp, price_type.value)

    def __get_volume(self, symbol: str) -> float:
        return self.quotes.get_quote(symbol).price_volume(self.current_timestamp)

    def fetch_timestamp(self) -> int:
        """
        Returns:
             Current time of exchange in millisecond.
        """
        return self.current_timestamp

    def fetch_markets(self) -> Tuple[dict, dict]:
        """
        Returns:
             (Supported assets, Supported trading pairs) in dictionary
        """
        return self.assets.copy(), self.symbols.copy()

    def deposit(self, asset: str, amount: float) -> float:
        """
        Returns:
            The amount of successfully deposited asset.
        """
        if amount <= 0:
            return 0
        if asset in self.total_balance:
            self.total_balance[asset] += amount
            self.available_balance[asset] += amount
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
        if asset in self.total_balance:
            if self.available_balance[asset] < amount:
                amount = self.available_balance[asset]
            self.total_balance[asset] -= amount
            self.available_balance[asset] -= amount
            return amount
        else:
            raise NotSupported

    def fetch_balance(self) -> dict:
        """
        Returns:
            Dictionary of form: {symbol: {'total': xxx, 'available': xxx, 'in order': xxx}, ...}
        """
        balance = {}
        for asset in self.total_balance:
            balance[asset] = {'total': self.total_balance[asset],
                              'available': self.available_balance[asset],
                              'in order': self.__frozen_balance(asset)}
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
            for symbol in self.symbols():
                quotes[symbol] = self.fetch_ticker(symbol)
            return quotes
        else:
            return self.quotes.get_quote(symbol).ohlcv(self.current_timestamp)

    def __execute_buy(self, order: Order, price: float, amount: float) -> bool:
        """
        This function does not check anything. It assumes in order balance has already been deducted from the available
        balance.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.get_side() is OrderSide.Buy
        is_filled = order.execute_transaction(
            order.generate_transaction(amount=amount, price=price, timestamp=self.current_timestamp))

        quote_name = order.get_quote_name()
        base_name = order.get_base_name()
        fee = self.fee_rate / 100.0 * amount

        self.total_balance[quote_name] += amount - fee
        self.available_balance[quote_name] += amount - fee
        self.total_balance[base_name] -= price * amount
        # self.available_balance[base_name] -= price * amount
        order.pay_fee(quote_name, fee)

        return is_filled

    def __execute_sell(self, order: Order, price: float, amount: float) -> bool:
        """
        This function does not check anything. It assumes in order balance has already been deducted from the available
        balance.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.get_side() is OrderSide.Sell
        is_filled = order.execute_transaction(
            order.generate_transaction(amount=amount, price=price, timestamp=self.current_timestamp))

        quote_name = order.get_quote_name()
        base_name = order.get_base_name()
        fee = self.fee_rate / 100.0 * price * amount

        self.total_balance[quote_name] -= amount
        # self.available_balance[quote_name] -= amount
        self.total_balance[base_name] += price * amount - fee
        self.available_balance[base_name] += price * amount - fee
        order.pay_fee(base_name, fee)

        return is_filled

    def __execute_market_order(self, order: Order) -> bool:
        """
        This function does not check if the order is invalid / does not raise InvalidOrder exceptions. It only checks
        the validity of the slippage model and if the balance is sufficient.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.get_type() is OrderType.Market and order.get_remaining() == order.get_amount()

        price, amount = self.slippage_model(price=self.__get_price(order.get_symbol(),
                                                                   self.buy_price if order.get_side() is OrderSide.Buy
                                                                   else self.sell_price),
                                            amount=order.get_remaining(),
                                            side=order.get_side(),
                                            type=order.get_type(),
                                            timestamp=self.current_timestamp,
                                            supplement_data=self.supplement_data)

        if price < 0 or amount != order.get_remaining():
            raise SlippageModelError

        if order.get_side() is OrderSide.Buy:
            base_name = order.get_base_name()
            if price * amount > self.available_balance[base_name]:
                raise InsufficientFunds
            # self.__execute_buy assumes in order balance has already been deducted
            self.available_balance[base_name] -= amount * price
            return self.__execute_buy(order, price, amount)
        elif order.get_side() is OrderSide.Sell:
            quote_name = order.get_quote_name()
            if order.get_remaining() > self.available_balance[quote_name]:
                raise InsufficientFunds
            # self.__execute_sell assumes in order balance has already been deducted
            self.available_balance[quote_name] -= amount
            return self.__execute_sell(order, price, amount)

    def __accept_market_order(self, order: Order):
        assert order.get_type() is OrderType.Market
        if order.get_symbol() not in self.symbols or order.get_amount() <= 0:
            raise InvalidOrder
        elif order.get_status() is OrderStatus.Cancelled:
            self.closed_orders.insert_order(order)
        else:
            # market order is never "open". if accepted, it is executed immediately
            self.__execute_market_order(order)
            assert order.get_status() is OrderStatus.Filled
            self.closed_orders.insert_order(order)
            print('[BackExchange] Market order {:s} accepted and executed. '.format(order.get_id()))

    def __execute_limit_order(self, order: Order):
        """
        This function does not check if the order is invalid / does not raise InvalidOrder exceptions. It does not check
        if the balance is sufficient neither. It only checks the validity of the slippage.

        Returns:
             A bool indicates whether the order is filled or not.
        """
        assert order.get_type() is OrderType.Limit

        price, amount = self.slippage_model(price=self.__get_price(order.get_symbol(),
                                                                   self.buy_price if order.get_side() is OrderSide.Buy
                                                                   else self.sell_price),
                                            amount=order.get_remaining(),
                                            side=order.get_side(),
                                            type=order.get_type(),
                                            timestamp=self.current_timestamp,
                                            supplement_data=self.supplement_data)

        if price < 0 or amount > order.get_remaining():
            raise SlippageModelError

        if order.get_side() is OrderSide.Buy and price <= order.get_price():
            self.__execute_buy(order, price, amount)

            if order.get_status() is OrderStatus.Filled:
                print('[BackExchange] Limit buy order {:s} filled. '.format(order.get_id()))
            else:
                print('[BackExchange] Limit buy order {:s} partially filled to {:2}%. '.format(order.get_id(),
                                                                                               order.get_filled_percentage()))
        elif order.get_side() is OrderSide.Sell and price >= order.get_price():
            self.__execute_sell(order, price, amount)

            if order.get_status() is OrderStatus.Filled:
                print('[BackExchange] Limit sell order {:s} filled. '.format(order.get_id()))
            else:
                print('[BackExchange] Limit sell order {:s} partially filled to {:2}%. '.format(order.get_id(),
                                                                                               order.get_filled_percentage()))

        return order.get_status()

    def __accept_limit_order(self, order: Order):
        assert order.get_type() is OrderType.Limit
        if order.get_symbol() not in self.symbols or order.get_amount() <= 0:
            raise InvalidOrder
        elif order.get_status() is OrderStatus.Cancelled:
            self.closed_orders.insert_order(order)
        else:
            if order.get_side() is OrderSide.Buy:
                base_name = order.get_base_name()
                if order.get_amount() * order.get_price() > self.available_balance[base_name]:
                    raise InsufficientFunds
                self.available_balance[base_name] -= order.get_amount() * order.get_price()
            if order.get_side() is OrderSide.Sell:
                quote_name = order.get_quote_name()
                if order.get_amount() > self.available_balance[quote_name]:
                    raise InsufficientFunds
                self.available_balance[quote_name] -= order.get_amount()
            order.open()
            self.open_orders.insert_order(order)
            print('[BackExchange] Limit order {:s} accepted. '.format(order.get_id()))

    def create_market_buy_order(self, *, symbol, amount):
        names = symbol.translate({ord(c): ' ' for c in '-/'}).split()  # names = [quote_name, base_name]
        return self.submitted_order.add_new_order(names[0], names[1], None, amount, OrderType.Market, OrderSide.Buy,
                                                  self.current_timestamp)

    def create_market_sell_order(self, *, symbol, amount):
        names = symbol.translate({ord(c): ' ' for c in '-/'}).split()  # names = [quote_name, base_name]
        return self.submitted_order.add_new_order(names[0], names[1], None, amount, OrderType.Market, OrderSide.Sell,
                                                  self.current_timestamp)

    def create_limit_buy_order(self, *, symbol, amount, price):
        names = symbol.translate({ord(c): ' ' for c in '-/'}).split()  # names = [quote_name, base_name]
        return self.submitted_order.add_new_order(names[0], names[1], price, amount, OrderType.Limit, OrderSide.Buy,
                                                  self.current_timestamp)

    def create_limit_sell_order(self, *, symbol, amount, price):
        names = symbol.translate({ord(c): ' ' for c in '-/'}).split()  # names = [quote_name, base_name]
        return self.submitted_order.add_new_order(names[0], names[1], price, amount, OrderType.Limit, OrderSide.Sell,
                                                  self.current_timestamp)

    def resolve_orders(self):
        # resolve submitted order
        while not self.submitted_order.is_empty():
            order = self.submitted_order.pop_order()
            if order.type is OrderType.Market:
                self.__accept_market_order(order)
            elif order.type is OrderType.Limit:
                self.__accept_limit_order(order)

        # resolve open orders
        for order_id in self.open_orders.get_all_order_id():
            order = self.open_orders.get_order(order_id)
            if self.__execute_limit_order(order):
                self.open_orders.remove_order(order)
                self.closed_orders.insert_order(order)

    def cancel_submitted_order(self, order_id: str):
        self.submitted_order.get_order(order_id).cancel()

    def cancel_open_order(self):
        pass

    def fetch_order(self, order_id: str):
        order = self.open_orders.get_order(order_id)
        if order is None:
            order = self.closed_orders.get_order(order_id)
        if order is None:
            raise OrderNotFound
        else:
            return order.get_info()

    def fetch_submitted_order(self, order_id: str) -> dict:
        return self.submitted_order.get_order(order_id).get_info()

    def fetch_open_orders(self, symbol=''):
        orders = []
        for order in self.open_orders:
            if symbol != '' and order.get_symbol() != symbol:
                continue
            else:
                orders.append(order.get_info())
        return orders

    def fetch_closed_orders(self, symbol=''):
        orders = []
        for order in self.closed_orders:
            if symbol != '' and order.get_symbol() != symbol:
                continue
            else:
                orders.append(order.get_info())
        return orders

    def fetch_orders(self, symbol=''):
        return self.fetch_open_orders(symbol) + self.fetch_closed_orders(symbol)

    def balance_consistency_check(self):
        pass

    def process_timestamp(self):
        print('[BackExchange] Current timestamp: {}'.format(self.current_timestamp))

        # process viable assets and pairs
        pass

        # resolve orders
        self.resolve_orders()



