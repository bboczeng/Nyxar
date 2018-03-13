from core.Ticker import TickerFields, BidAsks
from backtest.Order import OrderType, OrderSide


class SlippageBase(object):
    def __init__(self):
        pass

    def generate_tx(self, price: float, amount: float, order_type: OrderType, order_side: OrderSide, symbol: str,
                    ticker: dict, timestamp: int):
        return price, amount


class VolumeSlippage(SlippageBase):
    def __init__(self, tradable_rate: float=2.5):
        super(VolumeSlippage, self).__init__()
        self._rate = tradable_rate

    def generate_tx(self, price: float, amount: float, order_type: OrderType, order_side: OrderSide, symbol: str,
                    ticker: dict, timestamp: int):
        if order_type is not OrderType.Market:
            return price, min(amount, ticker['volume'] * self._rate / 100.0)
        else:
            return price, amount


class SpreadSlippage(SlippageBase):
    def __init__(self, bidask: BidAsks, spread_rate: float=50):
        super(SpreadSlippage, self).__init__()
        self._bidask = bidask
        self._rate = spread_rate

    def generate_tx(self, price: float, amount: float, order_type: OrderType, order_side: OrderSide, symbol: str,
                    ticker: dict, timestamp: int):
        try:
            bid = self._bidask.get_ticker(symbol).get_closet_value(timestamp, TickerFields.Bid)
            ask = self._bidask.get_ticker(symbol).get_closet_value(timestamp, TickerFields.Ask)
        except KeyError:
            return price, amount
        if order_side is OrderSide.Buy:
            return price + (ask - bid) * self._rate / 100.0, amount
        elif order_side is OrderSide.Sell:
            return price - (ask - bid) * self._rate / 100.0, amount


class SpreadVolumeSlippage(SlippageBase):
    def __init__(self, bidask: BidAsks, spread_rate: float=0.5, tradable_rate: float=2.5):
        super(SpreadVolumeSlippage, self).__init__()
        self._bidask = bidask
        self._srate = spread_rate
        self._vrate = tradable_rate

    def generate_tx(self, price: float, amount: float, order_type: OrderType, order_side: OrderSide, symbol: str,
                    ticker: dict, timestamp: int):
        if order_type is not OrderType.Market:
            amount = min(amount, ticker['volume'] * self._vrate / 100.0)

        # assuming ticker has 'symbol' as key
        try:
            bid = self._bidask.get_ticker(ticker['symbol']).get_closet_value(timestamp, TickerFields.Bid)
            ask = self._bidask.get_ticker(ticker['symbol']).get_closet_value(timestamp, TickerFields.Ask)
        except KeyError:
            return price, amount
        # use _srate in place of _rate
        if order_side is OrderSide.Buy:
            return price + (ask - bid) * self._srate / 100.0, amount
        elif order_side is OrderSide.Sell:
            return price - (ask - bid) * self._srate / 100.0, amount
