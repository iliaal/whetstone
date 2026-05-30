class Config:
    """A config object that caches a snapshot of its data."""

    def __init__(self):
        self._data = {"level": "info"}
        self._cache = None

    def get(self):
        if self._cache is None:
            self._cache = dict(self._data)
        return self._cache

    def update(self, key, value):
        self._data[key] = value
