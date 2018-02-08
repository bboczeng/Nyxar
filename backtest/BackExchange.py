from core.Quote import Quotes
from backtest.Order import * # do we use this?


class BackExchange(object):
    def __init__(self, quotes):
        assert isinstance(quotes, Quotes), "assets has to be Assets class"

        self.quotes = quotes
        self.balance = {}
        self.in_order = {}
        for asset in quotes.get_asset_list():
            self.balance[asset] = 0
            self.in_order[asset] = 0

        self.open_orders = OrderBook()
        self.history_orders = OrderBook()

        self.current_timestamp = 0

    def deposit(self, asset, amount):
        if asset in self.balance:
            self.balance[asset] += amount
        else:
            raise Exception("Asset not supported! ")

    def __get_free_balance(self, asset):
        return self.balance[asset] - self.in_order[asset]

    def withdraw(self, asset, amount):
        if asset in self.balance:
            withdrawable = self.__get_free_balance(asset)
            if withdrawable < amount:
                print("Insufficient funds, withdraw all remaining " + str(withdrawable))
                amount = withdrawable
            self.balance[asset] -= amount
        else:
            raise Exception("Currency not supported! ")

    def get_balance(self):
        balance = {}
        for asset in self.balance:
            balance[asset] = {'total': self.balance[asset], 'in_order': self.in_order[asset]}
        return balance

    def get_price(self, symbol=''):
        if symbol == '':
            quotes = {}
            for symbol in self.quotes.get_quote_list():
                quotes[symbol] = self.get_price(symbol)
            return quotes
        else:
            # should integrate as a method for Quote
            return {'symbol': self.quotes.get_quote(symbol).symbol,
                    'open': self.quotes.get_quote(symbol).price_open(self.current_timestamp),
                    'high': self.quotes.get_quote(symbol).price_high(self.current_timestamp),
                    'low': self.quotes.get_quote(symbol).price_low(self.current_timestamp),
                    'close': self.quotes.get_quote(symbol).price_close(self.current_timestamp),
                    'volume': self.quotes.get_quote(symbol).price_volume(self.current_timestamp)}

    def place_limit_order(self, quote_name, base_name, price, amount, side):
        if (quote_name + '/' + base_name) not in self.quotes.get_quote_list():
            print("Trading pair not exist! ")
        elif amount <= 0:
            print("Amount must be positive! ")
        elif price <= 0:
            print("Price must be positive! ")
        elif side == OrderSide.Buy and price * amount > self.__get_free_balance(base_name):
            price("Insufficient " + base_name)
        elif side == OrderSide.Sell and amount > self.__get_free_balance(quote_name):
            print("Insufficient " + quote_name)
        else:
            self.open_orders.add_new_order(quote_name, base_name, price, amount, OrderType.Limit,
                                           side, self.current_timestamp)
            self.in_order[base_name] += price * amount
            return True
        return False

    def place_market_order(self, quote_name, base_name, amount, side):
        if (quote_name + '/' + base_name) not in self.quotes.get_quote_list():
            print("Trading pair not exist! ")
        elif amount <= 0:
            print("Amount must be positive! ")
        elif side == OrderSide.Sell and amount > self.__get_free_balance(quote_name):
            print("Insufficient " + quote_name)
        else:
            self.open_orders.add_new_order(quote_name, base_name, None, amount, OrderType.Market,
                                           side, self.current_timestamp)
            return True
        return False

    def resolve_open_orders(self):
        finished = []
        for order in self.open_orders:
            if order.side == OrderSide.Buy:
                market_buy_price = self.quotes.get_quote(order.symbol).price_close(self.current_timestamp)
                if order.type == OrderType.Limit and order.price < market_buy_price:
                    continue
                to_fill = order.get_remaining() if (
                    order.get_remaining() * market_buy_price <= self.__get_free_balance(order.get_base_name())) \
                    else (self.__get_free_balance(order.get_base_name()) / market_buy_price)
                if order.execute_transaction(Transaction(order.quote_name, order.base_name, market_buy_price,
                                                         to_fill, OrderSide.Buy, self.current_timestamp)):
                    finished.append(order)
                self.balance[order.quote_name] += to_fill
                self.balance[order.base_name] -= market_buy_price * to_fill
            elif order.side == OrderSide.Sell:
                market_sell_price = self.quotes.get_quote(order.symbol).price_close(self.current_timestamp)
                if order.type == OrderType.Limit and order.price > market_sell_price:
                    continue
                to_fill = order.get_remaining()

                if order.execute_transaction(Transaction(order.quote_name, order.base_name, market_sell_price,
                                                         to_fill, OrderSide.Sell, self.current_timestamp)):
                    finished.append(order)
                self.balance[order.quote_name] -= to_fill
                self.balance[order.base_name] += market_sell_price * to_fill

        for order in finished:
            self.history_orders.insert_order(order)
            self.open_orders.remove_order(order)