from core.Ticker import TickerFields, BidAsks


class SlippageBase(object):
    def __init__(self):
        pass

    def generate_tx(self, price: float, amount: float, order_info: dict, ticker: dict, timestamp: int):
        return price, amount


class VolumeSlippage(SlippageBase):
    def __init__(self, tradable_rate: float=2.5):
        self._rate = tradable_rate

    def generate_tx(self, price: float, amount: float, order_info: dict, ticker: dict, timestamp: int):
        return price, min(amount, ticker['volume'] * self._rate / 100.0)


class SpreadSlippage(SlippageBase):
    def __init__(self, bidask: BidAsks, spread_rate: float=0.5):
        self._bidask = bidask
        self._rate = spread_rate

    def generate_tx(self, price: float, amount: float, order_info: dict, ticker: dict, timestamp: int):
        try:
            bid = self._bidask.get_ticker(order_info['symbol']).get_closet_value(timestamp, TickerFields.Bid)
            ask = self._bidask.get_ticker(order_info['symbol']).get_closet_value(timestamp, TickerFields.Ask)
        except KeyError:
            return price, amount
        if order_info['side'] == 'buy':
            return price + (ask - bid) * self._rate, amount
        elif order_info['side'] == 'sell':
            return price - (ask - bid) * self._rate, amount
