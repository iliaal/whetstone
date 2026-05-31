import copy


class Config:
    """Holds config data. snapshot() must return a fully isolated copy."""

    def __init__(self, data):
        self._data = data

    def snapshot(self):
        return self._data

    def update(self, key, value):
        self._data[key] = value
