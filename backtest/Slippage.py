from backtest.Order import OrderSide, OrderType, Transaction


class SlippageBase(object):
    def __init__(self):
        self._supplement_data = {}

    def generate_tx(self, *, price: float, amount: float, side: OrderSide, order_type: OrderType, ticker: dict,
                    timestamp: int):
        return price, amount


class VolumeSlippage(SlippageBase):
    def __init__(self, tradable_rate: float=2.5):
        super(VolumeSlippage, self).__init__()
        self._rate = tradable_rate

    def generate_tx(self, *, price: float, amount: float, side: OrderSide, order_type: OrderType, ticker: dict,
                    timestamp: int):
        return price, min(amount, ticker['volume'] * self._rate / 100.0)