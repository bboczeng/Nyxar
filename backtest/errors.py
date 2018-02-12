class BackExchangeError(Exception):
    pass


class NotSupported(BackExchangeError):
    pass


class InvalidSymbol(BackExchangeError):
    pass


class InsufficientFunds(BackExchangeError):
    pass


class InvalidOrder(BackExchangeError):
    pass


class OrderNotFound(InvalidOrder):
    pass


class SlippageModelError(Exception):
    pass
