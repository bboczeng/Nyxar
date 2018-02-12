from backtest.order import OrderSide, OrderType, Transaction
from typing import List, Set, Tuple


def slippage_base(*, price: float, amount: float, side: OrderSide, type: OrderType, timestamp: int,
                  supplement_data: dict) -> Tuple(float, float):
    return price, amount
