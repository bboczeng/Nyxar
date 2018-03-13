# to do: pytz support


class Timer(object):
    def __init__(self, start_time: int, end_time: int, ticker_size: int):
        self._start_time = start_time
        self._end_time = end_time
        self._step = ticker_size
        self._current_time = start_time

    @property
    def time(self):
        return self._current_time

    def next(self) -> bool:
        self._current_time += self._step
        if self._current_time > self._end_time:
            return True
        else:
            return False
